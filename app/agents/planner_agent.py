from typing import List

from app.config.settings import settings
from app.models.state import Task
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import PydanticOutputParser
from langchain_openai import ChatOpenAI

from app.services.ds_platform import ds_client
from app.utils.logger import logger


class PlannerAgent:
    def __init__(self):
        # self.llm = ChatOpenAI(temperature=0, model="gpt-3.5-turbo-16k")
        self.parser = PydanticOutputParser(pydantic_object=List[Task])

    async def make_plan(self, user_input: str, chatId: str) -> List[Task]:
        """
        拆分复杂用户需求为有序子任务
        """
        prompt = ChatPromptTemplate.from_messages([
            ("system", """
            你是低代码平台的任务规划智能体，需要将用户复杂需求拆分为按顺序执行的子任务，每个子任务对应LangGraph的节点名：
            1. 基础功能节点名对照：
                - 应用名提取对应节点名：app_name_extract
                - 应用创建对应节点名：app_create
                - 表单创建对应节点名：form_build
            2. 依赖关系规则：
                - app_name_extract 依赖 intent_recognition（且intent_type=app_build）；
                - app_create 依赖 app_name_extract；
                - form_build 依赖 app_create；
            3. 注意事项：
                - 子任务必须按「先创建应用，后创建表单」的顺序排列
                - 每个任务的status初始化为pending，task_id从1开始递增
                - 任务描述要清晰，包含具体的应用/表单名称及核心要求

            输出格式必须符合以下结构（严格遵循Pydantic List[Task]规范）：
            {format_instructions}
            """),
            ("user", "用户需求：{user_input}")
        ]).partial(format_instructions=self.parser.get_format_instructions())

        try:
            # response = await self.llm.ainvoke(prompt.format_prompt(user_input=user_input))
            response = await ds_client.call_llm(
                api_key=settings.DS_API_KEY_GENERAL_USE,
                chatId=chatId,
                prompt=prompt,
                stream=False,
                temperature=0.3
            )
            tasks = self.parser.parse(response.content)
            logger.info(f"会话{chatId}：规划智能体拆分出{len(tasks)}个子任务")
            return tasks
        except Exception as e:
            logger.error(f"会话{chatId}：规划智能体任务拆分失败：{str(e)}")
            # 兜底返回默认任务（针对会议预定应用场景）
            return [
                Task(
                    task_id=1,
                    node_name="app_name_extract",
                    description="解析用户需要生成的应用名称",
                    status="pending",
                    # output=None
                ),
                Task(
                    task_id=2,
                    node_name="app_create",
                    description="创建名为「会议预定」的应用",
                    status="pending",
                    # output=None
                ),
                Task(
                    task_id=3,
                    node_name="form_build",
                    description="创建「会议室信息」表单，包含会议室名称、楼层、房间号、最大容纳人数字段",
                    status="pending",
                    # output=None
                ),
                Task(
                    task_id=4,
                    node_name="form_build",
                    description="创建「会议室预订信息」表单，包含预订时间段字段",
                    status="pending",
                    # output=None
                )
            ]


# 全局规划智能体实例
planner_agent = PlannerAgent()