from typing import Literal
from app.services.ds_platform import ds_client
from app.config.settings import settings
from app.utils.logger import logger
from app.utils.exceptions import IntentRecognitionError


class AppNameExtractAgent:
    """应用名称识别智能体：识别要搭建的应用名称"""

    APP_NAME_EXTRACT_PROMPT_TEMPLATE = """
       你是应用搭建助手，需要从用户的输入中提取用户想搭建的应用名称关键词（不包含“应用”两个字）。  
    请根据用户输入，准确识别出描述应用功能或用途的核心词汇，并确保返回非空的应用名称。  
    
    示例：  
    - 输入：“搭建'请假申请'应用” → 输出：请假申请”  
    - 输入：“搭建请假申请应用” →输出：“请假申请”  
    - 输入：“我想做一个库存管理系统” → 输出：“库存管理”  
    - 输入：“创建一个员工档案应用” → 输出：“员工档案”  
    
    注意：  
    1. 直接提取用户描述中与应用功能相关的核心短语，忽略“应用”“系统”“平台”等泛化词汇。  
    2. 如果用户输入中未明确提及名称，则根据上下文推断一个合理且非空的应用名称（如“事务管理”“信息登记”等）。  
    3. 始终返回一个有效的应用名称，不得为空。  （重要）
    4. 不能包含特殊字符，符号。

    用户需求：{user_input}
    """

    @classmethod
    async def recognize_appname(cls, chatId, user_input: str) -> str:
        """
        识别应用名称
        :param user_input: 用户输入
        :return: 应用名称
        """
        prompt = cls.APP_NAME_EXTRACT_PROMPT_TEMPLATE.format(user_input=user_input)

        try:
            response = await ds_client.call_llm(
                api_key=settings.DS_API_KEY_INTENT,
                chatId=chatId,
                prompt=prompt,
                stream=False,
                temperature=0.0  # 意图识别用极低温度保证准确性
            )

            appName = response["content"].strip().lower()
            logger.info(f"分析出应用名称为：{appName}")

            if appName == "":
                raise IntentRecognitionError(f"无效的应用名称识别结果：{appName}")

            return appName
        except Exception as e:
            logger.error(f"应用名称识别失败：{str(e)}", exc_info=True)
            raise IntentRecognitionError(f"应用名称识别失败：{str(e)}")


# 全局实例
app_name_extract_agent = AppNameExtractAgent()
