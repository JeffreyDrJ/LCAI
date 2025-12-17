# app/utils/state_persistence.py（无Redis版本）
import json
import threading
from typing import Optional, Tuple, Any
from app.models.state import LCAIState
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, SystemMessage

# 内存缓存：key=session_id，value=(state, checkpoint)
_paused_states = {}
# 线程锁：保证多请求下的线程安全
_state_lock = threading.Lock()
# 缓存过期时间（秒）：默认30分钟
CACHE_EXPIRE_SECONDS = 1800


# 消息序列化/反序列化（和Redis版本一致）
def serialize_message(msg: BaseMessage) -> dict:
    return {
        "type": msg.type,
        "content": msg.content,
        "additional_kwargs": msg.additional_kwargs
    }


def deserialize_message(msg_dict: dict) -> BaseMessage:
    msg_type = msg_dict["type"]
    if msg_type == "human":
        return HumanMessage(**msg_dict)
    elif msg_type == "ai":
        return AIMessage(**msg_dict)
    elif msg_type == "system":
        return SystemMessage(**msg_dict)
    else:
        return BaseMessage(**msg_dict)


# 保存暂停的状态（内存版）
def save_paused_state(session_id: str, state: LCAIState, checkpoint: Any):
    """
    保存暂停的流程状态到内存
    :param session_id: 会话ID
    :param state: LCAIState对象
    :param checkpoint: LangGraph断点
    """
    with _state_lock:
        # 序列化state（避免对象引用问题）
        state_dict = state.dict()
        state_dict["messages"] = [serialize_message(msg) for msg in state_dict["messages"]]
        # 存储：(序列化的state, checkpoint, 过期时间戳)
        import time
        expire_at = time.time() + CACHE_EXPIRE_SECONDS
        _paused_states[session_id] = (state_dict, checkpoint, expire_at)


# 加载暂停的状态（内存版）
def load_paused_state(session_id: str) -> Tuple[Optional[LCAIState], Optional[Any]]:
    """
    从内存加载暂停的状态
    :return: (LCAIState, checkpoint)
    """
    with _state_lock:
        if session_id not in _paused_states:
            return None, None

        state_dict, checkpoint, expire_at = _paused_states[session_id]
        # 检查是否过期
        import time
        if time.time() > expire_at:
            del _paused_states[session_id]  # 清理过期状态
            return None, None

        # 反序列化state
        state_dict["messages"] = [deserialize_message(msg) for msg in state_dict["messages"]]
        state = LCAIState(**state_dict)
        return state, checkpoint


# 删除暂停的状态（内存版）
def delete_paused_state(session_id: str):
    with _state_lock:
        if session_id in _paused_states:
            del _paused_states[session_id]


# 定期清理过期状态（可选，防止内存泄漏）
def clean_expired_states():
    """后台线程定期清理过期状态"""
    import time
    while True:
        with _state_lock:
            expired_ids = []
            for session_id, (_, _, expire_at) in _paused_states.items():
                if time.time() > expire_at:
                    expired_ids.append(session_id)
            for session_id in expired_ids:
                del _paused_states[session_id]
        # 每5分钟清理一次
        time.sleep(300)


# 启动后台清理线程（程序启动时执行）
import threading

clean_thread = threading.Thread(target=clean_expired_states, daemon=True)
clean_thread.start()