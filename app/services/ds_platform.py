import httpx
from typing import Dict, Any, Optional
from app.config.settings import settings
from app.utils.logger import logger
from app.utils.exceptions import DSPlatformError


class DSPlatformClient:
    """宝武DS平台LLM调用客户端"""

    def __init__(self):
        self.base_url = settings.DS_BASE_URL
        self.timeout = 60
        self.client = httpx.AsyncClient(timeout=self.timeout)

    async def call_llm(
            self,
            api_key: str,
            prompt: str,
            stream: bool = False,
            temperature: float = 0.1
    ) -> Dict[str, Any]:
        """
        调用宝武DS平台LLM接口
        :param api_key: 智能体API密钥
        :param prompt: 提示词
        :param stream: 是否流式响应
        :param temperature: 生成温度
        :return: LLM响应结果
        """
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}"
        }

        payload = {
            "model": settings.DS_MODEL_NAME,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": temperature,
            "stream": stream
        }

        try:
            logger.info(f"调用DS平台LLM：model={settings.DS_MODEL_NAME}, stream={stream}")
            response = await self.client.post(
                url=self.base_url,
                headers=headers,
                json=payload
            )
            response.raise_for_status()

            if stream:
                # 流式响应返回生成器
                async def stream_generator():
                    async for chunk in response.aiter_text():
                        yield chunk

                return {"stream": stream_generator()}
            else:
                result = response.json()
                logger.info(f"DS平台响应：{result.get('choices')[0].get('message').get('content')[:50]}...")
                return {
                    "content": result.get("choices")[0].get("message").get("content"),
                    "usage": result.get("usage", {})
                }
        except httpx.HTTPStatusError as e:
            logger.error(f"DS平台HTTP错误：{e.response.status_code} - {e.response.text}")
            raise DSPlatformError(f"DS平台调用失败：{e.response.text}", e.response.status_code)
        except Exception as e:
            logger.error(f"DS平台调用异常：{str(e)}", exc_info=True)
            raise DSPlatformError(f"DS平台调用异常：{str(e)}")

    async def close(self):
        """关闭HTTP客户端"""
        await self.client.aclose()


# 全局DS平台客户端实例
ds_client = DSPlatformClient()