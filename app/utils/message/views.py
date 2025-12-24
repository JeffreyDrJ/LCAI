from typing import Literal, Dict

from app.models.state import LCAIState


# 2. 工具函数：推送中间消息（更新状态）
async def update_views(state: LCAIState, model_id:str, type:Literal["form", "process"], content: Dict) -> Dict:
    """更新状态中的视图信息"""
    views = state.views
    # 初始化结构
    views.setdefault(model_id, {}).setdefault(type, content)
    return views