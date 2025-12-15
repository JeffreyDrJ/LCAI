# app/models/state.py
from pydantic import BaseModel, Field
from typing import Optional, Literal, List
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage  # 标准消息类型
from app.models.schema import FormSchema  # 你的表单Schema类

# 1. 自定义带messages的基础状态类（替代LangGraph旧版MessagesState）
class BaseLCAIState(BaseModel):
    messages: List[BaseMessage] = Field(default_factory=list, description="对话消息列表")
    session_id: str = Field(..., description="会话ID")
    user_input: str = Field(..., description="用户当前输入")

# 2. 扩展核心状态类（纯Pydantic模型，无TypedDict）
class LCAIState(BaseLCAIState):
    # 意图识别结果
    intent_type: Optional[Literal["qa", "form_build", "unknown"]] = Field(default=None,description="意图类型：问答/表单搭建/未知")
    intent_desc: Optional[str] = Field(default=None, description="意图描述")

    # 表单相关数据
    form_schema: Optional[FormSchema] = Field(default=None, description="表单结构")
    form_save_status: Optional[Literal["success", "failed"]] = Field(default=None, description="表单保存状态")
    form_save_msg: Optional[str] = Field(default=None, description="表单保存提示")
    form_modify_history: List[str] = Field(default=[], description="表单修改历史")

    # 流程控制
    need_modify: bool = Field(default=False, description="是否需要修改表单")
    finished: bool = Field(default=False, description="流程是否结束")
    human_confirm: bool = Field(default=False, description="用户是否确认完成")

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