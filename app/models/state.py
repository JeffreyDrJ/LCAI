from langgraph.graph import MessagesState
from pydantic import BaseModel, Field
from typing import Optional, Dict, List, Literal
from app.models.schema import FormSchema


# 扩展LangGraph状态，包含LCAI专属数据
class LCAIState(MessagesState):
    # 基础会话信息
    session_id: str = Field(..., description="会话ID")
    user_input: str = Field(..., description="用户当前输入")

    # 意图识别结果
    intent_type: Optional[Literal["qa", "form_build", "unknown"]] = Field(default=None,
                                                                          description="意图类型：问答/表单搭建/未知")
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