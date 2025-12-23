# app/agents/executor_agent.py
from typing import Optional, Dict, Any

from langchain_core.messages import SystemMessage, AIMessage
from langgraph.constants import END
from langgraph.graph import add_messages

from app.models.state import LCAIState, Task
from app.utils.logger import logger


class ExecutorAgent:
    def __init__(self):
        # 移除原有 node_mapping 和执行方法，仅保留任务管理逻辑
        self.task_node_map = {
            "app_name_extract": "app_name_extract",
            "app_create": "app_create",
            "form_build": "form_build",
            "human_confirm": "human_confirm"
        }  # 任务节点名与 LangGraph 节点名映射（确保一致性）

    def get_next_pending_task(self, state: LCAIState) -> Optional[Task]:
        """
        获取任务队列中第一个待执行的任务（pending 状态）
        """
        if not state.execution_plan:
            logger.warning(f"会话{state.session_id}：任务队列为空")
            return None

        # 按 task_id 升序排序，获取第一个 pending 任务
        sorted_tasks = sorted(state.execution_plan, key=lambda t: t.task_id)
        next_task = next((t for t in sorted_tasks if t.status == "pending"), None)
        return next_task

    def get_target_node(self, task: Task) -> str:
        """
        根据任务节点名，获取对应的 LangGraph 功能节点名
        """
        target_node = self.task_node_map.get(task.node_name, "")
        if not target_node:
            logger.error(f"未知任务节点名：{task.node_name}，无法匹配 LangGraph 节点")
        return target_node

    def update_task_status(self, state: LCAIState, task_id: int, status: str,
                           output: Optional[Dict[str, Any]] = None) -> None:
        """
        更新指定任务的状态与执行结果
        """
        for task in state.execution_plan:
            if task.task_id == task_id:
                task.status = status
                task.task_output = output
                logger.info(f"会话{state.session_id}：任务{task_id}状态更新为「{status}」")
                break
        else:
            logger.warning(f"会话{state.session_id}：未找到任务ID {task_id}，无法更新状态")

    def is_all_tasks_completed(self, state: LCAIState) -> bool:
        """
        判断任务队列是否全部执行完成（无 pending/running 任务）
        """
        if not state.execution_plan:
            return True
        return all(t.status in ["success", "failed", "need_human"] for t in state.execution_plan)

    def validate_task(self, state: LCAIState) -> bool:
        """
        判断上一项任务是否成功：
        """
        node_name = state.execution_plan[int(state.current_task_id) - 1].node_name
        if node_name == "app_name_extract":
            return state.app_name != ""
        elif node_name == "app_create":
            return state.app_id != ""
        elif node_name == "form_build":
            return state.model_id != ""
        else:
            return True

    async def execute_next_step(self, state: LCAIState) -> Dict[str, Any]:
        """
        准备下一步流程：获取下一个任务，返回跳转节点信息
        """
        try:
            # 1. 判断是否所有任务已完成
            if self.is_all_tasks_completed(state):
                completed_count = len([t for t in state.execution_plan if t.status == "success"])
                total_count = len(state.execution_plan)
                feedback = f"任务队列执行完毕！共{total_count}个任务，成功{completed_count}个"
                logger.info(f"会话{state.session_id}：{feedback}")
                return {
                    "executing_plan": False,
                    "finished": True,
                    "planner_feedback": feedback,
                    "next_node": END,  # 所有任务完成，跳转至结束
                    "messages": add_messages(state.messages, [SystemMessage(content=feedback)])
                }
            # 2. 更新上一项任务状态
            if state.current_task_id != "" and state.current_task_id != None:
                task_success = self.validate_task(state)
                if task_success:
                    self.update_task_status(state, state.current_task_id, "success")

            # 2. 获取下一个待执行任务
            next_task = self.get_next_pending_task(state)
            if not next_task:
                feedback = "任务队列无待执行任务，流程结束"
                return {
                    "executing_plan": True,
                    "finished": True,
                    "planner_feedback": feedback,
                    "next_node": END,
                    "messages": add_messages(state.messages, [SystemMessage(content=feedback)])
                }

            # 3. 更新当前任务为 running 状态
            self.update_task_status(state, next_task.task_id, "running")

            # 4. 获取要跳转的 LangGraph 节点
            target_node = self.get_target_node(next_task)
            if not target_node:
                feedback = f"任务{next_task.task_id}（{next_task.node_name}）无法匹配功能节点，执行失败"
                self.update_task_status(state, next_task.task_id, "failed", {"error": feedback})
                return {
                    "executing_plan": False,
                    "current_task_id": next_task.task_id,
                    "planner_feedback": feedback,
                    "next_node": "executor_agent",  # 跳转回 executor，处理下一个任务
                    "messages": add_messages(state.messages, [AIMessage(content=feedback)])
                }

            # 5. 返回跳转信息
            feedback = f"即将执行任务{next_task.task_id}/{len(state.execution_plan)}：{next_task.description}，跳转至「{target_node}」节点"
            logger.info(f"会话{state.session_id}：{feedback}")
            return {
                "executing_plan": True,
                "current_task_id": next_task.task_id,
                "current_task_node": target_node,
                "planner_feedback": feedback,
                "next_node": target_node,  # 告诉 LangGraph 下一步跳转的节点
                "messages": add_messages(state.messages, [SystemMessage(content=feedback)])
            }
        except Exception as e:
            error_msg = f"Executor 准备下一步流程失败：{str(e)}"
            logger.error(f"会话{state.session_id}：{error_msg}")
            return {
                "executing_plan": False,
                "finished": True,
                "planner_feedback": error_msg,
                "next_node": END,
                "messages": add_messages(state.messages, [AIMessage(content=error_msg)])
            }


# 全局执行智能体实例
executor_agent = ExecutorAgent()