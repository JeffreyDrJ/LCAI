# 可放在 app/graph/hooks.py（新建钩子文件）或直接放在 lcai 接口文件中
import time
from typing import Dict, Any
from app.models.state import LCAIState

# 1. 节点-进度提示映射字典（与之前一致，可按需扩展）
NODE_PROGRESS_TIPS = {
    "app_template_query_node": "正在查询应用模板...",
    "planner_node": "正在生成任务规划...",
    "human_node": "正在等待用户确认...",
    "execute_task_node": "正在执行任务...",
    "save_form_node": "正在保存表单数据...",
}

# 2. 定义节点前置钩子（pre 钩子：节点执行前触发）
async def node_pre_hook(state: LCAIState, config: Dict[str, Any], node_info: Dict[str, Any]) -> LCAIState:
    """
    LangGraph 节点前置钩子：节点执行前生成进度提示
    :param state: 节点执行前的状态对象
    :param config: 会话配置（包含 thread_id 等）
    :param node_info: 节点信息（包含节点名称 node_id 等）
    :return: 更新后的状态（携带进度提示）
    """
    # 获取当前节点名称
    node_name = node_info["node_id"]
    # 排除 LangGraph 内置系统节点（如 __interrupt__）
    if node_name.startswith("__"):
        return state

    # 获取节点对应的进度提示（默认兜底提示）
    progress_tip = NODE_PROGRESS_TIPS.get(
        node_name,
        f"正在执行【{node_name}】节点..."
    )

    # 构建进度提示数据（与前端解析格式一致）
    progress_info = {
        "type": "progress",
        "node": node_name,
        "tip": progress_tip,
        "time": time.strftime('%Y-%m-%d %H:%M:%S'),
        "finished": False,
        "session_id": state.session_id
    }

    # 将进度提示添加到状态的 progress_tips 列表中
    state.progress_tips = progress_tip
    print(f"【钩子触发】节点 {node_name} 即将执行，进度提示：{progress_tip}")

    # 返回更新后的状态（LangGraph 会使用该状态执行节点）
    return state