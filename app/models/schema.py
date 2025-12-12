from pydantic import BaseModel, Field, field_validator
from typing import Optional, Dict, Any, List


# ------------------------------
# 1. 定义Meta元数据模型（核心规范）
# ------------------------------
class LCAIMeta(BaseModel):
    """LCAI接口元数据模型（对话及场景信息）"""
    # 必填字段
    chatId: str = Field(..., description="对话ID，用于控制多轮对话、新一轮对话，非空字符串")
    userId: str = Field(..., description="用户ID，用户唯一标识，非空字符串")
    lcUserName: str = Field(..., description="低代码平台用户名，非空字符串")
    origin: str = Field(..., description="低代码平台环境域名，非空字符串")

    # 可选字段
    cur_workspaceId: Optional[str] = Field(None, description="当前工作空间ID，辅助判断场景")
    cur_appId: Optional[str] = Field(None, description="当前应用ID，辅助判断场景")
    cur_modelId: Optional[str] = Field(None, description="当前表单ID，辅助判断场景")
    cur_page: Optional[str] = Field(None, description="当前页面标识，辅助判断场景")

    # 可选：自定义校验（比如chatId格式、userId非空等）
    @field_validator("chatId", "userId", "lcUserName", "origin")
    def validate_non_empty_str(cls, v):
        """校验必填字符串非空、非空白"""
        if not v or v.strip() == "":
            raise ValueError("字段不能为空或仅包含空白字符")
        return v.strip()


# LCAI-API请求入参规范
class LCAIRequest(BaseModel):
    user_input: str = Field(..., description="用户输入的自然语言需求")
    meta: LCAIMeta = Field(..., description="元数据（对话及场景信息），必填")  # 核心：meta为必填项
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
