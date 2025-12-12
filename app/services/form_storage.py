import httpx
from typing import Dict, Any
from app.config.settings import settings
from app.utils.logger import logger
from app.utils.exceptions import FormStorageError
from app.models.schema import FormSchema


class FormStorageClient:
    """表单保存第三方API客户端"""

    def __init__(self):
        self.base_url = settings.FORM_STORAGE_API_URL
        self.api_key = settings.FORM_STORAGE_API_KEY
        self.timeout = 30
        self.client = httpx.AsyncClient(timeout=self.timeout)

    async def save_form(self, form_schema: FormSchema) -> Dict[str, Any]:
        """
        保存表单到第三方系统
        :param form_schema: 表单结构
        :return: 保存结果
        """
        headers = {
            "Content-Type": "application/json",
            "X-API-Key": self.api_key
        }

        payload = form_schema.model_dump()

        try:
            logger.info(f"调用表单保存API：form_name={form_schema.form_name}")
            response = await self.client.post(
                url=self.base_url,
                headers=headers,
                json=payload
            )
            response.raise_for_status()

            result = response.json()
            logger.info(f"表单保存成功：form_id={result.get('form_id')}")
            return {
                "status": "success",
                "form_id": result.get("form_id"),
                "msg": "表单保存成功"
            }
        except httpx.HTTPStatusError as e:
            logger.error(f"表单保存HTTP错误：{e.response.status_code} - {e.response.text}")
            raise FormStorageError(f"表单保存失败：{e.response.text}", e.response.status_code)
        except Exception as e:
            logger.error(f"表单保存异常：{str(e)}", exc_info=True)
            raise FormStorageError(f"表单保存异常：{str(e)}")

    async def close(self):
        """关闭HTTP客户端"""
        await self.client.aclose()


# 全局表单保存客户端实例
form_storage_client = FormStorageClient()