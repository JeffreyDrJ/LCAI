import time

from fastapi import APIRouter, HTTPException, BackgroundTasks, Body
from fastapi.responses import StreamingResponse
from typing import Generator, Dict, Any
import json
from langchain_core.messages import HumanMessage, BaseMessage

from app.models.schema import LCAIRequest, LCAIResponse, LCAIStreamChunk, LCAIMeta
from app.models.state import LCAIState
from app.graph.lcai_graph import lcai_graph
from app.utils.logger import logger
from app.utils.exceptions import DSPlatformError, FormStorageError
from app.utils.state_persistence import load_paused_state, delete_paused_state, save_paused_state

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
            messages=[HumanMessage(content=request.user_input)]
        )

        # 生成流式响应
        async def stream_generator() -> Generator[str, None, None]:
            async for chunk in lcai_graph.astream(initial_state, stream_mode="updates"):
                # 检查是否触发暂停
                if chunk.get("paused") and chunk.get("pause_at") == "human_confirm":
                    # 保存暂停状态到内存（无需Redis）
                    save_paused_state(
                        session_id=request.meta.chatId,
                        state=LCAIState(**chunk),
                        checkpoint=chunk.get("graph_checkpoint")  # LangGraph断点
                    )
                for node_name, node_data in chunk.items():
                    if "messages" in node_data:
                        del node_data["messages"]
                    node_data["time"] = time.strftime('%Y-%m-%d %H:%M:%S')
                    print(f'会话{initial_state.session_id}|| 节点【{node_name}】输出:{node_data}')
                    # 流式返回消息内容（增量内容）
                    yield json.dumps(
                        node_data,
                        ensure_ascii=False  # 核心参数：禁用ASCII转义
                    )

            # 发送结束标识
            end_chunk = {
                "type": "end",
                "msg": "",
                "finished": True
            }
            yield json.dumps(
                end_chunk,
                ensure_ascii=False  # 核心参数：禁用ASCII转义
            )

        return StreamingResponse(
            stream_generator(),
            media_type="text/event-stream",
            headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"}
        )
    except Exception as e:
        logger.error(f"LCAI流式调用失败：{str(e)}", exc_info=True)
        # 发送错误流
        error_chunk = LCAIStreamChunk(
            msg=f"服务异常：{str(e)}",
            finished=True,
            session_id=request.meta.chatId
        )
        return StreamingResponse(
            [f"data: {error_chunk.model_dump_json(ensure_ascii=False)}\n\n"],
            media_type="text/event-stream"
        )

# 2. 二次请求：用户确认/修改（恢复流程）
@router.post("/lcai/confirm")
async def confirm_form(
        session_id: str = Body(..., embed=True),  # 会话ID（和首次请求一致）
        user_input: str = Body(..., embed=True)  # 用户输入：确认/修改
):
    try:
        # 从内存加载暂停的状态和断点
        paused_state, checkpoint = load_paused_state(session_id)
        if not paused_state:
            return {
                "code": -1,
                "message": "会话已过期或不存在，请重新发起表单搭建请求"
            }

        # 更新状态：传入用户新输入，取消暂停
        paused_state.user_input = user_input
        paused_state.paused = False
        paused_state.need_modify = True if user_input.lower() in ["修改", "否"] else False

        # 恢复流程执行
        async def stream_generator():
            async for chunk in lcai_graph.astream(
                    input=paused_state,
                    config={"checkpoint": checkpoint},  # 从断点恢复
                    stream_mode="values"
            ):
                if chunk.get("finished"):
                    # 流程完成，清理内存缓存
                    delete_paused_state(session_id)
                yield f"data: {json.dumps(chunk, ensure_ascii=False)}\n\n"

        return StreamingResponse(
            stream_generator(),
            media_type="text/event-stream",
            headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"}
        )

    except Exception as e:
        logger.error(f"二次请求失败：{str(e)}", exc_info=True)
        return {
            "code": -1,
            "message": f"确认失败：{str(e)}"
        }
