import httpx
import json
from typing import Dict, Any, Optional, AsyncGenerator
from app.config.settings import settings
from app.utils.logger import logger
from app.utils.exceptions import DSPlatformError


class DSPlatformClient:
    """宝武DS平台LLM调用客户端"""

    def __init__(self):
        self.base_url = settings.DS_BASE_URL
        self.timeout = 120  # 流式超时延长
        self.client = httpx.AsyncClient(timeout=self.timeout)

    async def _parse_stream_chunk(self, chunk: str) -> AsyncGenerator[str, None]:
        """解析DS平台流式chunk，仅返回增量content"""
        try:
            # 按换行符分割chunk，处理多行情况
            lines = chunk.strip().split("\n")
            for line in lines:
                line = line.strip()
                if not line or not line.startswith("data:"):
                    continue

                # 提取JSON部分
                json_str = line.lstrip("data:").strip()
                if json_str == "[DONE]":
                    continue

                # 解析单个JSON片段（此时是单行，无多段问题）
                data = json.loads(json_str)
                # 提取增量content（兼容content为null的情况）
                delta_content = data.get("choices", [{}])[0].get("delta", {}).get("content")
                if delta_content is not None and delta_content != "":
                    yield delta_content

        except json.JSONDecodeError as e:
            logger.error(f"JSON解析失败：{e}，原始行：{line[:200]}")
        except Exception as e:
            logger.error(f"解析流式chunk失败：{e}")

    async def call_llm(
            self,
            api_key: str,
            chatId: str,
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
            # "Content-Type": "application/json",
            "Accept": "application/json",
            "Authorization": f"Bearer {api_key}"
        }

        payload = {
            "model": settings.DS_MODEL_NAME,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": temperature,
            "stream": stream,
            "chatId": chatId
        }

        try:
            # logger.info(f"调用DS平台LLM：model={settings.DS_MODEL_NAME}, stream={stream}")
            response = await self.client.post(
                url=self.base_url + "/chat/completions",
                headers=headers,
                json=payload
            )
            response.raise_for_status()

            if stream:
                # 流式响应返回生成器（处理多行chunk）
                async def stream_generator() -> AsyncGenerator[str, None]:
                    async for raw_chunk in response.aiter_text():
                        # 调用修复后的解析方法，逐段返回content
                        async for content in self._parse_stream_chunk(raw_chunk):
                            # print(f"DS流式返回:{content}")
                            yield content  # 仅返回有效增量内容
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