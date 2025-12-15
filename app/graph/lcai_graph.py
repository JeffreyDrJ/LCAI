from langchain_core.messages import SystemMessage, AIMessage
from langgraph.graph import StateGraph, END
from langgraph.graph.message import add_messages
from typing import Dict, Any
from app.models.state import LCAIState
from app.agents.intent_agent import intent_agent
from app.agents.qa_agent import qa_agent
from app.agents.form_build_agent import form_build_agent
from app.agents.form_modify_agent import form_modify_agent
from app.services.form_storage import form_storage_client
from app.utils.logger import logger
from app.utils.exceptions import IntentRecognitionError, FormStorageError


# ------------------------------
# 1. 定义节点函数
# ------------------------------
async def intent_recognition_node(state: LCAIState) -> Dict[str, Any]:
    # 强制将字典转为LCAIState对象
    # if isinstance(state, dict):
    #     logger.warning("状态为字典，自动转换为LCAIState对象")
    #     state = LCAIState(**state)

    """意图识别节点：判断用户意图类型"""
    try:
        intent_type = await intent_agent.recognize_intent(state.user_input)
        return {
            "intent_type": intent_type,
            "intent_desc": f"识别到用户意图类型：{intent_type}",
            "messages": add_messages(state.messages, [SystemMessage(content=f"意图识别结果：{intent_type}")])
        }
    except IntentRecognitionError as e:
        logger.error(f"意图识别节点失败：{str(e)}")
        return {
            "intent_type": "unknown",
            "intent_desc": f"意图识别失败：{str(e)}",
            "finished": True,
            "messages": add_messages(state.messages,
                                     [AIMessage(content=f"抱歉，无法识别您的需求：{str(e)}")])
            # TODO 可默认转为调用问答智能体
        }


async def qa_agent_node(state: LCAIState) -> Dict[str, Any]:
    """低代码问答节点：处理问答类需求"""
    try:
        response = await qa_agent.answer(state.user_input, stream=False)
        return {
            "finished": True,
            "messages": add_messages(state.messages, [AIMessage(content=response["content"])])
        }
    except Exception as e:
        logger.error(f"问答智能体节点失败：{str(e)}")
        return {
            "finished": True,
            "messages": add_messages(state.messages,
                                     [AIMessage(content=f"抱歉，无法解答您的问题：{str(e)}")])
        }


async def form_build_node(state: LCAIState) -> Dict[str, Any]:
    """表单搭建节点：生成表单结构"""
    try:
        form_schema = await form_build_agent.build_form(state.user_input)
        return {
            "form_schema": form_schema,
            "messages": add_messages(state.messages, [AIMessage(
                content=f"已为您生成表单结构：{form_schema.model_dump_json(ensure_ascii=False)}"
            )])
        }
    except Exception as e:
        logger.error(f"表单搭建节点失败：{str(e)}")
        return {
            "finished": True,
            "messages": add_messages(state.messages, [AIMessage(content=f"抱歉，表单生成失败：{str(e)}")])
        }


async def form_save_node(state: LCAIState) -> Dict[str, Any]:
    """表单保存节点：调用第三方API保存表单"""
    if not state.form_schema:
        return {
            "form_save_status": "failed",
            "form_save_msg": "表单结构为空，保存失败",
            "finished": True,
            "messages": add_messages(state.messages, [AIMessage(content="表单结构为空，保存失败")])
        }

    try:
        save_result = await form_storage_client.save_form(state.form_schema)
        # 更新表单ID
        state.form_schema.form_id = save_result["form_id"]
        return {
            "form_save_status": "success",
            "form_save_msg": save_result["msg"],
            "form_schema": state.form_schema,
            "messages": add_messages(state.messages, [
                AIMessage(content=f"{save_result['msg']}，表单ID：{save_result['form_id']}"),
                AIMessage(content="请问您是否需要修改表单？如需修改请说明具体意见，如无需修改请回复“确认”")
            ])
        }
    except FormStorageError as e:
        logger.error(f"表单保存节点失败：{str(e)}")
        return {
            "form_save_status": "failed",
            "form_save_msg": str(e),
            "finished": True,
            "messages": add_messages(state.messages, [AIMessage(content=f"表单保存失败：{str(e)}")])
        }


async def form_modify_node(state: LCAIState) -> Dict[str, Any]:
    """表单修改节点：根据用户意见修改表单"""
    if not state.form_schema:
        return {
            "finished": True,
            "messages": add_messages(state.messages, [AIMessage(content="暂无表单结构可修改")])
        }

    try:
        new_form_schema = await form_modify_agent.modify_form(state.form_schema, state.user_input)
        # 更新修改历史
        modify_history = state.form_modify_history + [state.user_input]
        return {
            "form_schema": new_form_schema,
            "form_modify_history": modify_history,
            "messages": add_messages(state.messages, [
                AIMessage(content=f"已为您修改表单：{new_form_schema.model_dump_json(ensure_ascii=False)}"),
                AIMessage(content="请问您是否需要继续修改表单？如需修改请说明具体意见，如无需修改请回复“确认”")
            ])
        }
    except Exception as e:
        logger.error(f"表单修改节点失败：{str(e)}")
        return {
            "messages": add_messages(state.messages, [AIMessage(
                content=f"表单修改失败：{str(e)}，请问您是否需要重新修改？"
            )])
        }


async def human_confirm_node(state: LCAIState) -> Dict[str, Any]:
    """人在回路确认节点：判断用户是否需要继续修改"""
    user_input = state.user_input.lower()
    if "确认" in user_input or "满意" in user_input or "不需要" in user_input:
        return {
            "finished": True,
            "human_confirm": True,
            "messages": add_messages(state.messages, [AIMessage(content="表单搭建完成，感谢您的使用！")])
        }
    else:
        return {
            "need_modify": True,
            "messages": add_messages(state.messages, [SystemMessage(content="用户需要修改表单")])
        }


# ------------------------------
# 2. 定义分支判断函数
# ------------------------------
def intent_branch(state: LCAIState) -> str:
    """根据意图类型选择后续节点"""
    intent_type = state.intent_type
    if intent_type == "qa":
        return "qa_agent"
    elif intent_type == "form_build":
        return "form_build"
    else:
        return END


def form_save_branch(state: LCAIState) -> str:
    """表单保存后判断是否需要用户确认"""
    if state.form_save_status == "success":
        return "human_confirm"
    else:
        return END


def modify_branch(state: LCAIState) -> str:
    """判断是否需要修改表单"""
    if state.need_modify:
        return "form_modify"
    else:
        return END


def human_confirm_branch(state: LCAIState) -> str:
    """用户确认后判断流程走向"""
    if state.need_modify:
        return "form_modify"
    else:
        return END


# ------------------------------
# 3. 构建LangGraph状态图
# ------------------------------
def build_lcai_graph():
    """构建LCAI核心流程图"""
    graph = StateGraph(
        state_schema=LCAIState,  # 强制状态为LCAIState对象
        validate=True  # 启用状态校验（可选，增强类型检查）
    )

    # 添加节点
    graph.add_node("intent_recognition", intent_recognition_node)
    graph.add_node("qa_agent", qa_agent_node)
    graph.add_node("form_build", form_build_node)
    graph.add_node("form_save", form_save_node)
    graph.add_node("form_modify", form_modify_node)
    graph.add_node("human_confirm", human_confirm_node)

    # 设置入口节点
    graph.set_entry_point("intent_recognition")

    # 添加分支边
    graph.add_conditional_edges(
        "intent_recognition",
        intent_branch,
        {
            "qa_agent": "qa_agent",
            "form_build": "form_build",
            END: END
        }
    )

    # 表单搭建流程
    graph.add_edge("form_build", "form_save")
    graph.add_conditional_edges(
        "form_save",
        form_save_branch,
        {
            "human_confirm": "human_confirm",
            END: END
        }
    )

    # 人在回路判断
    graph.add_conditional_edges(
        "human_confirm",
        human_confirm_branch,
        {
            "form_modify": "form_modify",
            END: END
        }
    )

    # 表单修改后回到确认节点
    graph.add_edge("form_modify", "human_confirm")

    # 问答流程
    graph.add_edge("qa_agent", END)

    # 编译图
    app = graph.compile()
    logger.info("LCAI LangGraph流程编译完成")
    return app


# 全局流程实例
lcai_graph = build_lcai_graph()
