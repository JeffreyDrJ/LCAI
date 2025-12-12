from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List

# LCAI-API请求入参规范
class LCAIRequest(BaseModel):
    user_input: str = Field(..., description="用户输入的自然语言需求")
    session_id: str = Field(..., description="会话ID，用于多轮交互")
    stream: Optional[bool] = Field(default=False, description="是否流式响应")

# API响应模型
class LCAIResponse(BaseModel):
    code: int = Field(default=200, description="状态码")
    msg: str = Field(default="success", description="提示信息")
    data: Dict[str, Any] = Field(..., description="返回数据")
    session_id: str = Field(..., description="会话ID")

# 流式响应模型
class LCAIStreamChunk(BaseModel):
    chunk: str = Field(..., description="流式返回片段")
    finished: bool = Field(default=False, description="是否结束")
    session_id: str = Field(..., description="会话ID")

# 表单结构模型
class FormField(BaseModel):
    field_name: str = Field(..., description="字段名称")
    field_type: str = Field(..., description="字段类型：string/number/select/date")
    required: bool = Field(default=True, description="是否必填")
    options: Optional[List[str]] = Field(default=None, description="下拉框选项")
    placeholder: Optional[str] = Field(default=None, description="输入提示")

class FormSchema(BaseModel):
    form_id: Optional[str] = Field(default=None, description="表单ID")
    form_name: str = Field(..., description="表单名称")
    fields: List[FormField] = Field(..., description="表单字段列表")
    description: Optional[str] = Field(default=None, description="表单描述")