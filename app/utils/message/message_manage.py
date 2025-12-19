from app.models.state import LCAIState


# 2. 工具函数：推送中间消息（更新状态）
async def push_intermediate_msg(state: LCAIState, msg: str) -> LCAIState:
    """更新状态中的中间消息，触发流式输出"""
    state.intermediate_messages.append(msg)
    return state