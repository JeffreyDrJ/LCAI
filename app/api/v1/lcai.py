import time

from fastapi import APIRouter, HTTPException, BackgroundTasks, Body
from fastapi.responses import StreamingResponse
from typing import Generator, Dict, Any, AsyncGenerator
import json
from langchain_core.messages import HumanMessage, BaseMessage
from langgraph.types import Command

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
            meta=request.meta,
            messages=[HumanMessage(content=request.user_input)]
        )

        # 设置会话
        thread = {"configurable": {"thread_id": request.meta.chatId}}

        # 生成流式响应
        async def stream_generator() -> AsyncGenerator[str, None]:
            # 运行图形直到遇到中断
            async for chunk in lcai_graph.astream(initial_state, config=thread, stream_mode="updates"):
                for node_name, node_data in chunk.items():
                    if node_name == "__interrupt__":
                        # 中断节点的node_data是tuple，需要特殊处理
                        for interrupt in node_data:
                            data = interrupt.value
                            interrupt_info = {
                                "type": "interrupt",
                                "node": "__interrupt__",
                                "time": time.strftime('%Y-%m-%d %H:%M:%S'),
                                "pause_info": {
                                    "session_id": request.meta.chatId,
                                    "pause_at": data["pause_at"],
                                    "message": data["question"],
                                    "sysMsg":"流程已暂停，请通过 /lcai/confirm 接口继续"
                                },
                                "finished": False
                            }
                            print(f'会话{initial_state.session_id}|| 遇到中断节点【{data["pause_at"]},等待用户响应中...】')
                            yield json.dumps(interrupt_info, ensure_ascii=False) + "\n\n"
                    else:
                        if "messages" in node_data:
                            del node_data["messages"]
                        if "execution_plan" in node_data:
                            del node_data["execution_plan"]
                        # node_data["time"] = time.strftime('%Y-%m-%d %H:%M:%S')
                        print(f'会话{initial_state.session_id}|| 节点【{node_name}】输出:{node_data}')
                        # 流式返回消息内容（增量内容）
                        yield json.dumps(
                            node_data,
                            ensure_ascii=False  # 核心参数：禁用ASCII转义
                        )

            # async for chunk in lcai_graph.astream(initial_state, config=thread, stream_mode="values"):
            #     print(chunk)
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


# 二次调用接口：用户确认/继续
@router.post("/confirm")
async def confirm_lcai(
        session_id: str = Body(..., embed=True),  # 会话ID（和首次请求一致）
        user_input: str = Body(..., embed=True)  # 用户输入："是"表示继续
):
    """
    二次调用LCAI智能体 - 处理用户确认
    :param session_id: 会话ID
    :param user_input: 用户输入（"是"表示继续执行）
    :return: 流式响应结果
    """
    try:
        logger.info(f"二次调用LCAI: session_id={session_id}, user_input={user_input}")

        # 构建继续执行的配置
        config = {
            "configurable": {"thread_id": session_id},
        }

        # 构建新的状态（包含用户的确认输入）
        new_state = {
            "user_input": user_input,
            "paused": False
        }

        # 生成流式响应
        async def stream_generator() -> AsyncGenerator[str, None]:
            # 从检查点恢复执行
            async for chunk in lcai_graph.astream(Command(resume=user_input), config=config, stream_mode="updates"):
                for node_name, node_data in chunk.items():
                    if node_name == "__interrupt__":
                        # 中断节点的node_data是tuple，需要特殊处理
                        interrupt_info = {
                            "type": "interrupt",
                            "node": "__interrupt__",
                            "time": time.strftime('%Y-%m-%d %H:%M:%S'),
                            "pause_info": {
                                "session_id": session_id,
                                "message": "流程已暂停，请通过 /lcai/confirm 接口继续"
                            },
                            "finished": False
                        }
                        print(f'会话{session_id}|| 遇到中断节点【{node_name}】')
                        yield json.dumps(interrupt_info, ensure_ascii=False) + "\n\n"
                    else:
                        if "messages" in node_data:
                            del node_data["messages"]
                        # node_data["time"] = time.strftime('%Y-%m-%d %H:%M:%S')
                        print(f'会话{session_id}|| 节点【{node_name}】输出:{node_data}')
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
            session_id=session_id
        )
        return StreamingResponse(
            [f"data: {error_chunk.model_dump_json(ensure_ascii=False)}\n\n"],
            media_type="text/event-stream"
        )
