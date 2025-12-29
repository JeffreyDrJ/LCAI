# app/models/state.py
from pydantic import BaseModel, Field
from typing import Optional, Literal, List, Any, Dict
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage  # 标准消息类型
from app.models.schema import FormSchema, LCAIMeta  # 你的表单Schema类


# 1. 自定义带messages的基础状态类（替代LangGraph旧版MessagesState）
class BaseLCAIState(BaseModel):
    messages: List[BaseMessage] = Field(default_factory=list, description="对话消息列表")
    session_id: str = Field(..., description="会话ID")
    user_input: str = Field(..., description="用户当前输入")
    meta: Optional[LCAIMeta] = Field(default=None, description="低代码元数据")

# 2. 规划智能体生成的子任务结构（核心自定义类）
class Task(BaseModel):
    # 1. 任务唯一标识（用于区分不同子任务）
    task_id: int
    # 2. 对应LangGraph的节点名（如intent_recognition/app_create，执行器据此调度节点）
    node_name: str
    # 3. 任务描述（用于日志、调试、人工查看）
    description: str = Field(default="", description="任务描述")
    # 4. 任务需求的参数
    task_input: Optional[Dict] = None
    # 5. 任务状态（严格约束取值，避免非法状态）
    status: Literal["pending", "running", "success", "failed", "need_human"]
    # 6. 任务执行结果（节点运行后的输出，比如intent_recognition返回的intent_type）
    task_output: Optional[Dict] = None

# 新增：TaskPlan 包装类（必须直接继承 BaseModel，无泛型嵌套问题）
class TaskPlan(BaseModel):
    tasks: List[Task] = Field(default_factory=list, description="有序子任务列表")

# 3. 扩展核心状态类（纯Pydantic模型，无TypedDict）
class LCAIState(BaseLCAIState):
    # 意图识别结果
    intent_type: str = Field(default=None,description="意图类型：问答/表单搭建/未知")
    intent_desc: Optional[str] = Field(default=None, description="意图描述")
    # 消息相关数据
    code: int = Field(default=0, description="状态码")
    type: str = Field(default="message", description="返回信息")
    node: str = Field(default="unknown", description="发消息的节点")
    msg: Optional[str] = Field(default=None, description="回答内容")
    intermediate_messages: List = Field(default_factory=list, description="中间返回消息")
    # 应用相关数据
    app_id: str = Field(default="", description="应用id")
    app_name: str = Field(default="", description="应用名称")
    # 应用模板数据
    app_templates: List = Field(default_factory=list, description="应用模板列表")
    choose_app_template: int = Field(default=-1, description="用户选择的应用模板号")
    # 表单相关数据
    model_id: str = Field(default="", description="表单id")
    form_name: str = Field(default="", description="表单中文名")
    views: Optional[Dict[str,Dict]] = Field(default={}, description="表单流程等信息")
    form_schema: Optional[FormSchema] = Field(default=None, description="表单结构")
    form_save_status: Optional[Literal["success", "failed"]] = Field(default=None, description="表单保存状态")
    form_save_msg: Optional[str] = Field(default=None, description="表单保存提示")
    form_modify_history: List[str] = Field(default=[], description="表单修改历史")
    # 表单多轮修改控制
    need_modify: bool = Field(default=False, description="是否需要修改表单")
    finished: bool = Field(default=False, description="流程是否结束")
    pre_finish: bool = Field(default=False, description="流程是否进入结束监听")
    human_confirm: bool = Field(default=False, description="用户是否确认完成")
    # 人工节点控制
    invoke_confirm_node: str = Field(default="", description="请求人工确认的节点id")
    paused: bool = Field(default=False, description="流程是否暂停")
    pause_at: Optional[str] = None  # 暂停的节点（如 "human_confirm"）
    question: str = Field(default="", description="中断提示")
    question_type: str = Field(default="confirm", description="中断类型")
    question_select: List = Field(default=[], description="中断选择信息")
    graph_checkpoint: Optional[Any] = None  # LangGraph流程断点
    goto: str = Field(default="", description="要跳转到的节点id")
    # 规划智能体新增字段
    executing_plan: bool = Field(default=False, description="执行智能体是否运行中")
    execution_plan: List[Task] = Field(default_factory=list)  # 执行计划（子任务列表）
    current_task_id: Optional[int] = None  # 当前执行的任务ID
    planner_feedback: Optional[str] = None  # 规划智能体的反馈/调整说明
    # 前置钩子
    progress_tips: str = Field(default="", description="节点前钩子提示")


# 验证：实例化后必须是Pydantic对象，而非dict
if __name__ == "__main__":
    test_state = LCAIState(
        session_id="123",
        user_input="测试",
        messages=[HumanMessage(content="测试")]
    )
    print(f"类型：{type(test_state)}")  # 应输出 <class 'app.models.state.LCAIState'>
    print(f"是否是dict：{isinstance(test_state, dict)}")  # 应输出 False
    print(f"messages属性：{test_state.messages}")  # 正常访问
