from typing import Literal

from app.services import query_app_templates
from app.services.ds_platform import ds_client
from app.config.settings import settings
from app.utils.logger import logger
from app.utils.exceptions import IntentRecognitionError


class ApptemplateQueryAgent:
    """模板查询智能体：识别用户意图类型"""

    keys = "" # 应用名称提取出的关键词,以逗号分隔
    app_templates = []

    APP_TEMPLATE_QUERY_KEYS_PROMPT_TEMPLATE = """
    你是应用搭建助手，需要从用户的输入中提取描述应用核心场景的**关键词**（单个或2字核心词汇为主，优先提炼最核心的场景指向词）。
    请根据用户输入，精准识别与应用功能、用途强相关的核心词根，确保返回非空、简洁的关键词。
    
    示例：
    - 输入：“搭建'请假申请'应用” → 输出：请假
    - 输入：“搭建请假申请应用” → 输出：请假
    - 输入：“我想做一个库存管理系统” → 输出：库存,管理系统
    - 输入：“创建一个员工档案应用” → 输出：员工,档案
    - 输入：“租户申请流程搭建” → 输出：租户
    - 输入：“做一个合同审批工具” → 输出：合同
    - 输入：“搭建办公用品领用系统” → 输出：办公用品,领用
    - 输入：“想做一个客户信息登记平台” → 输出：客户,信息登记
    - 输入：“搭建报销申请相关应用” → 输出：报销
    
    注意：
    1. 优先提取2字核心关键词，聚焦应用的核心服务对象、业务动作或场景主体，忽略“应用”“系统”“平台”“工具”“流程”“相关”等泛化词汇；
    2. 若用户输入包含多个相关词汇（如“员工档案管理”），取最核心的主体词（如“员工”）或动作词（如“管理”），优先选择更具场景辨识度的词汇；
    3. 如果用户输入未明确提及具体场景，根据上下文推断简洁合理的核心关键词（如输入“搭建一个内部审批应用”→输出：审批；输入“做一个日常事务工具”→输出：事务）；
    4. 始终返回一个有效的关键词，不得为空，且不包含特殊字符、符号、标点；
    5. 关键词以单个2字词为主，避免长短语，确保提炼后的词汇具备强场景指向性。
    6. 若提取出多个关键词，请用逗号分隔返回。

    应用名称：{appName}
    """

    @classmethod
    async def query_app_templates(cls, meta, appName: str) -> str:
        """
        查询应用模板
        :param appName: 应用名称
        :return: 应用模板集合
        """

        # 1.识别关键词
        prompt = cls.APP_TEMPLATE_QUERY_KEYS_PROMPT_TEMPLATE.format(appName=appName)

        try:
            response = await ds_client.call_llm(
                api_key=settings.DS_API_KEY_INTENT,
                chatId=meta.chatId,
                prompt=prompt,
                stream=False,
                temperature=0.0  # 意图识别用极低温度保证准确性
            )

            keys = response["content"].strip().lower()
            logger.info(f"应用名称{appName}拆分关键词结果：{keys}")

            if keys == "":
                raise IntentRecognitionError(f"无效的应用名称关键词识别结果：{keys}")
        except Exception as e:
            logger.error(f"应用模板查询失败：{str(e)}", exc_info=True)
            raise IntentRecognitionError(f"应用模板查询失败：{str(e)}")
        # 2.查询应用模板
        try:
            response = await query_app_templates.call_app_template_query(
                name_clues=keys,
                meta=meta
            )
            app_templates = response["result"]

            return app_templates
        except Exception as e:
            logger.error(f"应用模板查询失败：{str(e)}", exc_info=True)
            raise IntentRecognitionError(f"应用模板查询失败：{str(e)}")
# 全局实例
app_template_query_agent = ApptemplateQueryAgent()
