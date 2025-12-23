from typing import Dict, Any, Optional
from app.models.state import LCAIState, Task
from app.utils.logger import logger
import asyncio


class ExecutorAgent:
    def __init__(self):
        self.node_mapping = {
            "app_name_extract": self._execute_app_name_extract,
            "app_create": self._execute_app_create,
            "form_build": self._execute_form_build
        }

    async def _execute_app_name_extract(self, state: LCAIState, task: Task) -> Dict[str, Any]:
        """执行应用名提取任务"""
        from app.agents.appname_extract_agent import app_name_extract_agent
        try:
            # 从任务描述中提取应用名称
            app_name = "会议预定"  # 可通过NLP提取，此处简化
            app_info = await app_name_extract_agent.create_app(appName=app_name, meta=state.meta)
            return {
                "task_status": "success",
                "task_output": app_info,
                "app_id": app_info["app_id"],
                "app_name": app_info["app_name"]
            }
        except Exception as e:
            logger.error(f"任务{task.task_id}执行失败：{str(e)}")
            return {
                "task_status": "failed",
                "task_output": str(e)
            }

    async def _execute_app_create(self, state: LCAIState, task: Task) -> Dict[str, Any]:
        """执行应用创建任务"""
        from app.agents.app_create_agent import app_create_agent
        try:
            # 从任务描述中提取应用名称
            app_name = "会议预定"  # 可通过NLP提取，此处简化
            app_info = await app_create_agent.create_app(appName=app_name, meta=state.meta)
            return {
                "task_status": "success",
                "task_output": app_info,
                "app_id": app_info["app_id"],
                "app_name": app_info["app_name"]
            }
        except Exception as e:
            logger.error(f"任务{task.task_id}执行失败：{str(e)}")
            return {
                "task_status": "failed",
                "task_output": str(e)
            }

    async def _execute_form_build(self, state: LCAIState, task: Task) -> Dict[str, Any]:
        """执行表单创建任务"""
        from app.agents.form_build_agent import form_build_agent
        try:
            # 从任务描述中提取表单名称和提示
            form_name = task.description.split("「")[1].split("」")[0]
            form_prompt = task.description
            model_info = await form_build_agent.build_form(state=state, form_name=form_name, form_prompt=form_prompt)
            return {
                "task_status": "success",
                "task_output": model_info,
                "model_id": model_info["model_id"],
                "form_name": model_info["form_name"]
            }
        except Exception as e:
            logger.error(f"任务{task.task_id}执行失败：{str(e)}")
            return {
                "task_status": "failed",
                "task_output": str(e)
            }

    async def execute_task_queue(self, state: LCAIState) -> LCAIState:
        """
        执行任务队列中的所有子任务
        """
        state.executing_plan = True
        task_list = state.execution_plan
        total_tasks = len(task_list)

        for idx, task in enumerate(task_list):
            if task.status != "pending":
                continue

            # 更新当前任务ID与任务状态
            state.current_task_id = task.task_id
            task.status = "running"
            logger.info(f"开始执行任务{task.task_id}/{total_tasks}：{task.description}")

            # 调度对应节点执行
            if task.node_name not in self.node_mapping:
                task.status = "failed"
                task.output = f"未知节点名：{task.node_name}"
                state.planner_feedback = f"任务{task.task_id}无法执行：未知节点"
                continue

            # 执行任务
            task_result = await self.node_mapping[task.node_name](state, task)

            # 更新任务状态与输出
            task.status = task_result["task_status"]
            task.output = task_result["task_output"]

            # 将任务结果同步到全局状态
            if task_result["task_status"] == "success":
                for key, value in task_result.items():
                    if key not in ["task_status", "task_output"]:
                        setattr(state, key, value)
                logger.info(f"任务{task.task_id}执行成功")
            else:
                state.planner_feedback = f"任务{task.task_id}执行失败：{task_result['task_output']}"
                logger.error(f"任务{task.task_id}执行失败：{task_result['task_output']}")
                # 可选：中断任务队列或继续执行后续任务
                # break

        # 所有任务执行完毕
        state.executing_plan = False
        state.finished = all(task.status in ["success", "failed"] for task in task_list)
        state.planner_feedback = f"任务队列执行完成，共{total_tasks}个任务，成功{len([t for t in task_list if t.status == 'success'])}个"
        logger.info(f"会话{state.session_id}：任务队列执行完成")
        return state


# 全局执行智能体实例
executor_agent = ExecutorAgent()