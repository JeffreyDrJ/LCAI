from app.services.ds_platform import ds_client
from app.config.settings import settings
from app.utils.logger import logger


class QAAgent:
    """低代码问答智能体：处理平台使用帮助类问题"""

    QA_PROMPT_TEMPLATE = """
    你是低代码平台智能助手，请详细解答用户的问题，回答要清晰、易懂、贴合低代码平台使用场景：
    用户问题：{user_input}
    """

    @classmethod
    async def answer(cls, chatId: str, user_input: str, stream: bool = False) -> dict:
        """
        回答用户的低代码平台使用问题
        :param user_input: 用户问题
        :param stream: 是否流式响应
        :return: 回答结果
        """
        prompt = cls.QA_PROMPT_TEMPLATE.format(user_input=user_input)

        logger.info(f"低代码问答智能体处理请求：{user_input[:50]}...")
        response = await ds_client.call_llm(
            api_key=settings.DS_API_KEY_QA,
            chatId=chatId,
            prompt=prompt,
            stream=stream,
            temperature=0.3
        )

        return response


# 全局实例
qa_agent = QAAgent()