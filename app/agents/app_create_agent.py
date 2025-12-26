from typing import Literal, Dict, Any

from app.models.state import LCAIState
from app.services import query_app_templates, appservice
from app.services.ds_platform import ds_client
from app.config.settings import settings
from app.utils.logger import logger
from app.utils.exceptions import IntentRecognitionError, AppGenerateError


class AppCreateAgent:
    """应用创建智能体"""

    app_Id = ""  # 生成的应用id
    app_name = ""  # 生成的应用名称
    modelId = ""  # 生成的表单id

    FORM_JSON_GENERATE_PROMPT_TEMPLATE = """
    
    """

    @classmethod
    async def create_app(cls, meta, appName: str) -> Dict[str, Any]:
        """
        创建新应用
        :param appName: 应用名称
        :return: 应用模板集合
        """

        # 1.生成新应用
        try:
            response = await appservice.generate_app(
                app_name=appName,
                meta=meta
            )
            app_Id = response["app_id"];
            app_name = response["app_name"];

            return {
                "app_id": app_Id,
                "app_name": app_name,
            }


        except Exception as e:
            logger.error(f"应用生成失败：{str(e)}", exc_info=True)
            raise AppGenerateError(f"应用生成失败：{str(e)}")

    @classmethod
    async def activate_app_template(cls, state: LCAIState) -> Dict[str, Any]:
        """
        启用应用模板
        :param appName: 应用名称
        :return: 应用模板集合
        """
        # 1.获取应用模板
        app_template = []
        if len(state.app_templates) and state.choose_app_template > 0:
            app_template = state.app_templates[state.choose_app_template - 1]
        else:
            logger.error(f"应用生成失败：未找到应用模板！", exc_info=True)
            raise AppGenerateError(f"应用生成失败：未找到应用模板！")
        # 2.启用应用模板
        try:
            response = await appservice.activate_template(
                app_name=state.app_name,
                app_template=app_template,
                meta=state.meta
            )
            app_Id = response["app_id"];
            app_name = response["app_name"];

            return {
                "app_id": app_Id,
                "app_name": app_name,
            }


        except Exception as e:
            logger.error(f"应用生成失败：{str(e)}", exc_info=True)
            raise AppGenerateError(f"应用生成失败：{str(e)}")


# 全局实例
app_create_agent = AppCreateAgent()
