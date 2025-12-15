from fastapi import APIRouter, HTTPException, BackgroundTasks
from fastapi.responses import StreamingResponse
from typing import Generator, Dict, Any

from langchain_core.messages import HumanMessage

from app.models.schema import LCAIRequest, LCAIResponse, LCAIStreamChunk, LCAIMeta
from app.models.state import LCAIState
from app.graph.lcai_graph import lcai_graph
from app.utils.logger import logger
from app.utils.exceptions import DSPlatformError, FormStorageError

router = APIRouter(prefix="/lcai", tags=["LCAI核心接口"])


# 同步调用接口
@router.post("/invoke", response_model=LCAIResponse)
async def invoke_lcai(request: LCAIRequest):
    """
    同步调用LCAI智能体
    :param request: LCAI请求参数
    :return: 同步响应结果
    """
    try:
        logger.info(f"同步调用LCAI: 用户：{request.meta.userId}-{request.meta.lcUserName} | 环境：{request.meta.origin} "
                    f"| 场景信息：workspace={request.meta.cur_workspaceId}, app={request.meta.cur_appId}, form={request.meta.cur_modelId} | user_input={request.user_input[:50]}...")

        # 构建初始状态
        initial_state = LCAIState(
            session_id=request.meta.chatId,
            user_input=request.user_input,
            messages=[HumanMessage(content=request.user_input)]
            # 可选：将meta存入状态，供智能体流程使用（比如根据origin选择不同DS平台环境）
            # meta=LCAIMeta.model_dump()
        )
        logger.info(f"初始状态类型：{type(initial_state)}")  # 必须输出 <class 'app.models.state.LCAIState'>

        # 执行LangGraph流程
        result = await lcai_graph.ainvoke(initial_state)  # 注意返回时为 dict类型

        # 简化对话内容
        conversation = []
        for msg in result["messages"]:
            # 仅保留user/assistant角色，用属性访问替代get()
            if msg.type in ["human", "ai"]:
                conversation.append({
                    "role": msg.type,  # ✅ 消息对象属性
                    "content": msg.content  # ✅ 消息对象属性
                })

        # 构建响应
        response_data = {
            "intent_type": result.get("intent_type"),
            "intent_desc": result.get("intent_desc"),
            "form_schema": result.get("form_schema").model_dump() if result.get("form_schema") else None,
            "form_save_status": result.get("form_save_status"),
            "form_save_msg": result.get("form_save_msg"),
            "modify_history": result.get("form_modify_history"),
            "conversation": conversation,
            "meta": request.meta.model_dump()
        }

        return LCAIResponse(
            code=200,
            msg="success",
            data=response_data,
            session_id=request.meta.chatId
        )
    except DSPlatformError as e:
        logger.error(f"DS平台调用失败：{str(e)}")
        raise HTTPException(status_code=e.code, detail=e.message)
    except FormStorageError as e:
        logger.error(f"表单保存失败：{str(e)}")
        raise HTTPException(status_code=e.code, detail=e.message)
    except Exception as e:
        logger.error(f"LCAI同步调用失败：{str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"服务异常：{str(e)}")


# 流式调用接口
@router.post("/stream")
async def stream_lcai(request: LCAIRequest):
    """
    流式调用LCAI智能体
    :param request: LCAI请求参数
    :return: 流式响应结果
    """
    try:
        logger.info(f"同步调用LCAI: 用户：{request.meta.userId}-{request.meta.lcUserName} | 环境：{request.meta.origin} "
                    f"| 场景信息：workspace={request.meta.cur_workspaceId}, app={request.meta.cur_appId}, form={request.meta.cur_modelId} | user_input={request.user_input[:50]}...")

        # 构建初始状态
        initial_state = LCAIState(
            session_id=request.meta.chatId,
            user_input=request.user_input,
            messages=[{"role": "user", "content": request.user_input}]
        )

        # 生成流式响应
        async def stream_generator() -> Generator[str, None, None]:
            async for chunk in lcai_graph.astream(initial_state):
                # 提取assistant消息
                if "messages" in chunk and chunk["messages"]:
                    last_msg = chunk["messages"][-1]
                    if last_msg.get("role") == "assistant":
                        stream_chunk = LCAIStreamChunk(
                            chunk=last_msg.get("content", ""),
                            finished=False,
                            session_id=request.meta.chatId
                        )
                        yield f"data: {stream_chunk.model_dump_json(ensure_ascii=False)}\n\n"

            # 发送结束标识
            end_chunk = LCAIStreamChunk(
                chunk="",
                finished=True,
                session_id=request.meta.chatId
            )
            yield f"data: {end_chunk.model_dump_json(ensure_ascii=False)}\n\n"

        return StreamingResponse(
            stream_generator(),
            media_type="text/event-stream",
            headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"}
        )
    except Exception as e:
        logger.error(f"LCAI流式调用失败：{str(e)}", exc_info=True)
        # 发送错误流
        error_chunk = LCAIStreamChunk(
            chunk=f"服务异常：{str(e)}",
            finished=True,
            session_id=request.meta.chatId
        )
        return StreamingResponse(
            [f"data: {error_chunk.model_dump_json(ensure_ascii=False)}\n\n"],
            media_type="text/event-stream"
        )
