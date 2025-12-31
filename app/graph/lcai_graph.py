from langchain_core.messages import SystemMessage, AIMessage
from langchain_core.runnables.graph import MermaidDrawMethod
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from typing import Dict, Any, AsyncGenerator

from requests_toolbelt import user_agent

from app.agents.executor_agent import executor_agent
from app.agents.form_modify_agent import form_modify_agent
from app.agents.planner_agent import planner_agent
from app.config.settings import settings
from app.models.state import LCAIState

from app.agents.intent_agent import intent_agent
from app.agents.qa_agent import qa_agent
from app.agents.appname_extract_agent import app_name_extract_agent
from app.agents.app_template_query_agent import app_template_query_agent
from app.agents.app_create_agent import app_create_agent
from app.agents.form_build_agent import form_build_agent

from app.utils.logger import logger
from app.utils.exceptions import IntentRecognitionError, AppnameRecognitionError, AppGenerateError, PlanningError
from langgraph.types import interrupt, Command
from langgraph.types import Command
from app.graph.hooks import node_pre_hook  # 导入前置钩子
from app.utils.website import get_app_run_url


# ------------------------------
# 1. 定义节点函数
# ------------------------------
async def intent_recognition_node(state: LCAIState) -> Dict[str, Any]:
    """意图识别节点：判断用户意图类型"""
    try:
        intent_type = await intent_agent.recognize_intent(user_input=state.user_input, chatId=state.session_id)
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
        }


async def planner_node(state: LCAIState) -> Dict[str, Any]:
    """任务规划节点：拆分复杂用户需求"""
    try:
        plan = await planner_agent.make_plan(user_input=state.user_input, chat_id=state.session_id)

        return {
            "execution_plan": plan,
            "msg": "",
            "invoke_confirm_node": "planner_node" if len(plan) > 0 else ""
        }
    except PlanningError as e:
        logger.error(f"任务规划节点失败：{str(e)}")
        return {
            "execution_plan": [],
            "intent_desc": f"任务规划失败：{str(e)}",
            "finished": True,
            "messages": add_messages(state.messages,
                                     [AIMessage(content=f"抱歉，任务规划失败：{str(e)}")])
        }


async def executor_node(state: LCAIState) -> Dict[str, Any]:
    """执行节点：调度执行子任务队列"""
    try:
        # 调用 ExecutorAgent 准备下一步队列任务
        next_step_info = await executor_agent.execute_next_step(state)
        # 提取状态更新内容
        # 返回状态更新（包含下一步跳转节点信息）
        return {
            "current_task_id": next_step_info.get("current_task_id"),
            "current_task_node": next_step_info.get("current_task_node"),
            "planner_feedback": next_step_info.get("planner_feedback"),
            "goto": next_step_info.get("next_node"),
            "finished": next_step_info.get("finished", False),
            "messages": next_step_info.get("messages", state.messages),
            "execution_plan": state.execution_plan,  # 同步更新后的任务队列
            "executing_plan": next_step_info.get("executing_plan", False)  # 同步更新后的任务队列
        }
    except Exception as e:
        logger.error(f"执行节点执行失败：{str(e)}")
        return {
            "finished": True,
            "planner_feedback": f"执行节点执行失败：{str(e)}",
            "messages": add_messages(state.messages, [AIMessage(content=f"抱歉，任务执行失败：{str(e)}")])
        }


async def qa_agent_node(state: LCAIState) -> AsyncGenerator[Dict, None]:
    """低代码问答节点：处理问答类需求"""
    try:
        # 调用问答智能体，获取流式生成器
        qa_result = await qa_agent.answer(user_input=state.user_input, chatId=state.session_id, stream=True)
        stream_generator = qa_result.get("stream")
        answer = ""
        if stream_generator:
            # 逐段yield增量内容（核心：每一个chunk都实时返回）
            async for chunk in stream_generator:
                answer = answer + chunk
                # print(f"DS返回：{chunk}")
                yield {
                    "node": "qa_agent",
                    "messages": add_messages(state.messages, [AIMessage(content=answer)]),
                    "msg": answer,
                    "finished": False,
                }
    except Exception as e:
        logger.error(f"问答节点失败：{e}")
        # 异常兜底yield
        yield {
            "code": -1,
            "node": "qa_agent",
            "msg": f"问答失败：{e}",
            "finished": True,
        }


async def appname_extract_node(state: LCAIState) -> Dict[str, Any]:
    """应用名提取节点：根据用户需求提取出应用名称"""
    try:
        app_name = await app_name_extract_agent.recognize_appname(user_input=state.user_input, chatId=state.session_id)
        return {
            "app_name": app_name,
            "msg": f"已提取到应用名：[{app_name}], 正在查询相关的应用模板...",
            "messages": add_messages(state.messages, [SystemMessage(content=f"应用名提取结果：{app_name}")])
        }
    except AppnameRecognitionError as e:
        logger.error(f"应用名提取节点失败：{str(e)}")
        return {
            "app_name": "unknown",
            "desc": f"意图识别失败：{str(e)}",
            "finished": True,
            "messages": add_messages(state.messages,
                                     [AIMessage(content=f"应用名提取节点失败：{str(e)}")])
        }


async def app_template_query_node(state: LCAIState) -> Dict[str, Any]:
    """应用模板查询节点：根据应用名称查询相关应用模板"""
    try:
        app_templates = await app_template_query_agent.query_app_templates(appName=state.app_name, meta=state.meta)
        # 组织返回消息
        template_names = [template["templateCname"] for template in app_templates]
        return {
            "app_templates": app_templates,
            "messages": add_messages(state.messages,
                                     [SystemMessage(content=f"共获取到：{len(template_names)}个应用模板。")]),
            "msg": "",
            "invoke_confirm_node": "app_template_query_node" if len(template_names) > 0 else ""
        }
    except AppnameRecognitionError as e:
        logger.error(f"应用名提取节点失败：{str(e)}")
        return {
            "app_name": "unknown",
            "desc": f"意图识别失败：{str(e)}",
            "finished": True,
            "messages": add_messages(state.messages,
                                     [AIMessage(content=f"应用名提取节点失败：{str(e)}")])
        }


async def app_create_node(state: LCAIState) -> Dict[str, Any]:
    """创建一个新的应用"""
    msg = ""
    try:
        if state.choose_app_template < 0:
            # 纯创建新应用
            app_info = await app_create_agent.create_app(appName=state.app_name, meta=state.meta)
            msg = "应用创建成功，正在设计表单..."
            website = ""
        else:
            # 启用应用模板
            app_info = await app_create_agent.activate_app_template(state)
            msg = f"已通过应用模板创建应用：[{state.app_name}]"
            website = get_app_run_url(state.meta.origin, state.meta.cur_workspaceId, app_info["app_id"])
        # 组织返回消息
        return {
            "app_id": app_info["app_id"],
            "app_name": app_info["app_name"],
            "messages": add_messages(state.messages, [SystemMessage(content=f"应用创建成功:[{app_info["app_name"]}]")]),
            "msg": msg,
            "website": website
        }
    except AppGenerateError as e:
        logger.error(f"应用创建失败：{str(e)}")
        return {
            "app_name": "unknown",
            "desc": f"应用创建失败：{str(e)}",
            "finished": True,
            "messages": add_messages(state.messages, [AIMessage(content=f"应用创建失败：{str(e)}")])
        }


async def form_build_node(state: LCAIState) -> Dict[str, Any]:
    """创建一个新的表单"""
    try:
        model_info = await form_build_agent.build_form(state=state, form_name="", form_prompt="")
        # 组织返回消息
        model_id = model_info["model_id"]
        form_name = model_info["form_name"]
        return {
            "model_id": model_id,
            "form_name": form_name,
            "views": model_info["views"],
            "messages": add_messages(state.messages, [SystemMessage(content=f"表单创建成功:[{form_name}]")]),
            "msg": f"表单【{form_name}({model_id})】创建成功！",
            "website": get_app_run_url(state.meta.origin, state.meta.cur_workspaceId, state.app_id)
        }
    except AppGenerateError as e:
        logger.error(f"应用创建失败：{str(e)}")
        return {
            "app_name": "unknown",
            "desc": f"应用创建失败：{str(e)}",
            "finished": True,
            "messages": add_messages(state.messages, [AIMessage(content=f"应用创建失败：{str(e)}")])
        }


async def form_modify_node(state: LCAIState) -> Dict[str, Any]:
    """修改表单"""
    try:
        model_info = await form_modify_agent.modify_form(state=state, modify_opinion=state.user_input)
        # 组织返回消息
        model_id = model_info["model_id"]
        form_name = model_info["form_name"]
        return {
            "views": model_info["views"],
            "msg": f"表单修改完毕。",
            "website": get_app_run_url(state.meta.origin, state.meta.cur_workspaceId, state.app_id)
        }
    except AppGenerateError as e:
        logger.error(f"应用创建失败：{str(e)}")
        return {
            "app_name": "unknown",
            "desc": f"应用创建失败：{str(e)}",
            "finished": True,
            "messages": add_messages(state.messages, [AIMessage(content=f"应用创建失败：{str(e)}")])
        }


async def human_node(state: LCAIState) -> Dict[str, Any]:
    """人工确认节点：暂停流程等待用户输入"""
    # 问题
    question = ""
    question_type = "confirm"
    question_select = []
    if state.invoke_confirm_node == "app_template_query_node":
        template_names = [template["templateCname"] for template in state.app_templates]
        question = f"查询到以下相关应用模板，请选择是否启用模板："
        question_type = "select"
        for idx, template in enumerate(state.app_templates, start=1):
            question_select.append({
                "index": idx,
                "key": template["templateCname"],
                "value": str(idx)
            })
        question_select.append({
            "index": -1,
            "key": "通过智能体生成应用",
            "value": -1
        })
    elif state.invoke_confirm_node == "planner_node":
        question += "任务规划如下，请确认是否执行？（是/否）"
        question_type = "confirm"
        for task in state.execution_plan:
            question += f"\n{task.task_id}.{task.description}"
    # 使用interrupt暂停流程
    action = interrupt(
        {
            "question": question,
            "question_type": question_type,
            "question_select": question_select,
            "paused": True,
            "pause_at": state.invoke_confirm_node
        }
    )
    goto = ""
    params = {}
    print(f"\n\n\n会话：{state.meta.chatId}恢复执行！用户输入：{action}")

    if state.invoke_confirm_node == "app_template_query_node":
        """询问用户是否使用模板"""
        try:
            template_no = int(action)
            if template_no > 0:
                params["choose_app_template"] = template_no
            goto = "app_create"
        except ValueError:
            # 如果没选择模板，也没说要新增，就从头开始意图分析
            goto = "intent_recognition"
    elif state.invoke_confirm_node == "planner_node":
        if action == "是":
            goto = "executor_node"
        else:
            goto = END
        # return Command(goto=goto, update={"paused": False, "pause_at": "", "invoke_confirm_node": ""})
    # 这个函数会在用户回复后继续执行
    # 返回一个标识，表示需要等待用户输入
    return {
        **params,
        "paused": False,
        "pause_at": "",
        "goto": goto
    }


async def chat_listener_node(state: LCAIState) -> Dict[str, Any]:
    """监听节点，用于激活二轮对话"""
    hint = ""

    # 使用interrupt暂停流程
    user_input = interrupt(
        {
            "question": hint,
            "paused": True,
            "pre_finish": True,
            "pause_at": "chat_listener",
        }
    )
    # 监听恢复：
    print(f"\n\n\n会话：{state.meta.chatId}恢复执行！用户输入：{user_input}")

    return {
        "paused": False,
        "pause_at": "",
        "user_input": user_input,
        #重置参数：
        "choose_app_template": -1,
    }


# ------------------------------
# 2. 定义分支判断函数 (用于条件分支边判断)
# ------------------------------
def intent_branch(state: LCAIState) -> str:
    """根据意图类型选择后续节点"""
    intent_type = state.intent_type
    if intent_type == "qa":
        return "qa_agent"
    elif intent_type == "app_build":
        return "app_build"
    elif intent_type == "form_modify":
        return "form_modify"
    elif intent_type == "complex":
        return "complex"
    else:
        return "qa_agent"


def app_template_query_branch(state: LCAIState) -> str:
    """根据模板个数考虑是否进入用户选择节点"""
    app_templates = state.app_templates
    if len(app_templates) == 0:
        return "app_create"
    else:
        return "human_confirm"


def planner_agent_branch(state: LCAIState) -> str:
    """任务规划"""
    if (settings.HUMAN_CONFIRM_PLAN):
        return "human_confirm"
    else:
        return "executor_agent"


def executor_agent_branch(state: LCAIState) -> str:
    """任务执行"""
    return state.goto


def human_confirm_branch(state: LCAIState) -> str:
    """用户确认后判断流程走向"""
    # 检查用户输入
    if state.executing_plan:
        return "executor_agent"
    else:
        return state.goto

def app_name_extract_branch(state: LCAIState) -> str:
    """提取用户名称"""
    if state.executing_plan:
        return "executor_agent"
    else:
        return "app_template_query"


def app_create_branch(state: LCAIState) -> str:
    """提取用户名称"""
    if state.executing_plan:
        return "executor_agent"
    elif state.choose_app_template > 0:
        return END
    else:
        return "form_build"


def form_build_branch(state: LCAIState) -> str:
    """搭建表单"""
    if state.executing_plan:
        return "executor_agent"
    else:
        return END

def form_modify_branch(state: LCAIState) -> str:
    """修改表单"""
    if state.executing_plan:
        return "executor_agent"
    else:
        return END


# ------------------------------
# 3. 构建LangGraph状态图
# ------------------------------
def build_lcai_graph():
    """构建LCAI核心流程图"""
    graph = StateGraph(
        state_schema=LCAIState,  # 强制状态为LCAIState对象
        validate=False  # 启用状态校验（可选，增强类型检查）
    )

    ## 1/3 注册节点
    graph.add_node("intent_recognition", intent_recognition_node)
    graph.add_node("planner_agent", planner_node)
    graph.add_node("executor_agent", executor_node)
    graph.add_node("qa_agent", qa_agent_node)
    graph.add_node("app_name_extract", appname_extract_node)
    graph.add_node("app_template_query", app_template_query_node)
    graph.add_node("app_create", app_create_node)
    graph.add_node("form_build", form_build_node)
    graph.add_node("form_modify", form_modify_node)
    graph.add_node("human_confirm", human_node)
    graph.add_node("chat_listener", chat_listener_node)

    # 设置入口节点
    graph.set_entry_point("intent_recognition")

    ## 2/3 添加分支边
    # 添加分支边 - 意图识别
    graph.add_conditional_edges(
        "intent_recognition",
        intent_branch,
        {
            "qa_agent": "qa_agent",
            "app_build": "app_name_extract",
            "form_modify": "form_modify",
            "complex": "planner_agent",
            "unknown": "qa_agent",
            END: END
        }
    )
    # 添加分支边 - 任务规划
    graph.add_conditional_edges(
        "planner_agent",
        planner_agent_branch,
        {
            "human_confirm": "human_confirm",
            "executor_agent": "executor_agent",
            END: END
        }
    )
    # 添加分支边 - 任务执行
    graph.add_conditional_edges(
        "executor_agent",
        executor_agent_branch,
        {
            "app_name_extract": "app_name_extract",
            "app_create": "app_create",
            "form_build": "form_build",
            "human_confirm": "human_confirm",
            END: "chat_listener"
        }
    )

    # 添加分支边 - 问答节点
    graph.add_edge("qa_agent", END)

    # 添加分支边 - 结束监听节点
    graph.add_edge("chat_listener", "intent_recognition")

    # 添加分支边 - 提取应用名称
    graph.add_conditional_edges(
        "app_name_extract",
        app_name_extract_branch,
        {
            "executor_agent": "executor_agent",
            "app_template_query": "app_template_query"
        }
    )

    # 添加分支边 - 创建应用
    graph.add_conditional_edges(
        "app_create",
        app_create_branch,
        {
            "executor_agent": "executor_agent",
            "form_build": "form_build",
            END: "chat_listener"
        }
    )

    # 添加分支边 - 搭建表单
    graph.add_conditional_edges(
        "form_build",
        form_build_branch,
        {
            "executor_agent": "executor_agent",
            END: "chat_listener"
        }
    )

    # 添加分支边 - 修改表单
    graph.add_conditional_edges(
        "form_modify",
        form_modify_branch,
        {
            "executor_agent": "executor_agent",
            END: "chat_listener"
        }
    )

    # 添加分支边 - 查询应用模板
    graph.add_conditional_edges(
        "app_template_query",
        app_template_query_branch,
        {
            "app_create": "app_create",
            "human_confirm": "human_confirm",
        }
    )

    # 添加分支边 - 人工确认
    graph.add_conditional_edges(
        "human_confirm",
        human_confirm_branch,
        {
            "intent_recognition": "intent_recognition",
            "app_create": "app_create",
            # "": "app_create",
            END: END
        }
    )

    # 记忆初始化
    memory = MemorySaver()

    # 编译LangGraph流程图
    app = graph.compile(checkpointer=memory)
    logger.info("LCAI LangGraph流程编译完成")
    # 保存图片
    # graph_png = app.get_graph().draw_mermaid_png(max_retries=5, retry_delay=2.5)
    # with open("breakpoint.png", "wb") as f:
    #     f.write(graph_png)
    #     logger.info("流程图保存成功: breakpoint.png")

    # 返回
    return app


# 全局流程实例
lcai_graph = build_lcai_graph()
