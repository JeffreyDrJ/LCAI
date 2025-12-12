from typing import Literal
from app.services.ds_platform import ds_client
from app.config.settings import settings
from app.utils.logger import logger
from app.utils.exceptions import IntentRecognitionError


class IntentAgent:
    """需求判断智能体：识别用户意图类型"""

    INTENT_PROMPT_TEMPLATE = """
    请分析用户输入的需求，判断其意图类型，仅返回以下选项中的一个：
    1. qa：低代码平台使用帮助、问答类需求
    2. form_build：搭建/修改低代码表单相关需求
    3. unknown：无法识别的意图

    用户输入：{user_input}
    """
    #TODO 把提示词模板整合封装到LangchainTemplate里
    @classmethod
    async def recognize_intent(cls, user_input: str) -> Literal["qa", "form_build", "unknown"]:
        """
        识别用户意图
        :param user_input: 用户输入
        :return: 意图类型
        """
        prompt = cls.INTENT_PROMPT_TEMPLATE.format(user_input=user_input)

        try:
            response = await ds_client.call_llm(
                api_key=settings.DS_API_KEY_INTENT,
                prompt=prompt,
                stream=False,
                temperature=0.0  # 意图识别用极低温度保证准确性
            )

            intent = response["content"].strip().lower()
            logger.info(f"意图识别结果：{intent}，用户输入：{user_input}")

            if intent not in ["qa", "form_build", "unknown"]:
                raise IntentRecognitionError(f"无效的意图识别结果：{intent}")

            return intent
        except Exception as e:
            logger.error(f"意图识别失败：{str(e)}", exc_info=True)
            raise IntentRecognitionError(f"意图识别失败：{str(e)}")


# 全局实例
intent_agent = IntentAgent()