from typing import Literal

from app.services import query_app_templates, generate_new_app
from app.services.ds_platform import ds_client
from app.config.settings import settings
from app.utils.logger import logger
from app.utils.exceptions import IntentRecognitionError


class AppCreateAgent:
    """应用创建智能体"""

    app_Id = "" # 生成的应用id
    app_name = "" # 生成的应用名称
    modelId = "" # 生成的表单id

    FORM_JSON_GENERATE_PROMPT_TEMPLATE = """
    
    """

    @classmethod
    async def create_app(cls, meta, appName: str) -> str:
        """
        查询应用模板
        :param appName: 应用名称
        :return: 应用模板集合
        """

        # 1.生成新应用
        try:
            response = await generate_new_app.generate_app(
                app_name=appName,
                meta=meta
            )
            app_Id = response["app_id"];
            app_name = response["app_name"];

        # 2.生成表单JSON

        # 3.生成表单

        except Exception as e:
            logger.error(f"应用生成失败：{str(e)}", exc_info=True)
            raise IntentRecognitionError(f"应用生成失败：{str(e)}")
# 全局实例
app_create_agent = AppCreateAgent()
