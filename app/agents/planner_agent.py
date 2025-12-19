from typing import Dict

from app.services.ds_platform import ds_client
from app.config.settings import settings
from app.utils.logger import logger


class PlannerAgent:
    """低代码问答智能体：处理平台使用帮助类问题"""

    PLANNER_PROMPT_TEMPLATE = """
    你是低代码应用构建的规划智能体，需要根据用户需求生成结构化的执行计划。
    规则：
    1. 可调用的节点列表：intent_recognition（意图识别）、qa_agent（问答）、app_name_extract（应用名提取）、app_template_query（模板查询）、app_create（应用创建）、human_confirm（人工确认）；
    2. 执行计划需包含子任务的ID、节点名、描述、依赖关系（前置任务ID）、初始状态（pending）；
    3. 依赖关系规则：
       - app_name_extract 依赖 intent_recognition（且intent_type=app_build）；
       - app_template_query 依赖 app_name_extract；
       - human_confirm 依赖 app_template_query（且模板数>0）；
       - app_create 依赖 human_confirm 或 app_template_query（且模板数=0）；
       - qa_agent 无依赖（intent_type=qa时执行）；
    4. 当需要用户确认模板时，必须加入human_confirm任务；
    5. 输出格式为JSON，示例：
    [
        {"task_id": 1, "node_name": "intent_recognition", "description": "识别用户意图是问答还是构建应用", "dependencies": [], "status": "pending", "output": null},
        {"task_id": 2, "node_name": "app_name_extract", "description": "提取应用名称", "dependencies": [1], "status": "pending", "output": null}
    ]
    """

    @classmethod
    async def make_plan(cls, user_input: str, meta) -> dict:
        """
        回答用户的低代码平台使用问题
        :param user_input: 用户问题
        :param stream: 是否流式响应
        :return: 回答结果
        """
        prompt = cls.PLANNER_PROMPT_TEMPLATE.format(user_input=user_input)

        logger.info(f"低代码规划智能体处理请求：{user_input[:50]}...")
        response = await ds_client.call_llm(
            api_key=settings.DS_API_KEY_QA,
            chatId=meta.chatId,
            prompt=prompt,
            stream=False,
            temperature=0.3
        )

        return response


# 全局实例
planner_agent = PlannerAgent()
