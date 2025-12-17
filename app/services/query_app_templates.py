# 查询应用模板
from typing import Dict

import requests
import json
from app.utils.logger import logger
from app.utils.exceptions import AppTemplateApiError

# 第三方API配置
APP_TEMPLATE_API_URL = "https://eplatdev.baocloud.cn/code-admin/service/S_BE_LA_18"
API_TIMEOUT = 60  # 超时时间（秒）


async def call_app_template_api(name_clues, origin: str, meta: Dict) -> Dict:
    """
    调用应用模板查询API（S_BE_LA_18）
    :param user_input: 用户表单搭建需求（如“设备报修表单”）
    :param meta: 元数据（包含userId、origin等环境信息）
    :return: API响应结果
    """
    try:
        # 构造POST请求参数（根据第三方API要求调整，这里假设需要userInput和meta信息）
        request_body = {
            "userInput": name_clues,
            "meta": {
                "userId": meta.get("userId"),
                "origin": meta.get("origin"),
                "cur_workspaceId": meta.get("cur_workspaceId"),
                "cur_appId": meta.get("cur_appId")
            }
        }

        # 发送POST请求（同步请求，若需异步可改用aiohttp）
        response = requests.post(
            url=APP_TEMPLATE_API_URL.replace("https://eplatdev.baocloud.cn", origin),
            json=request_body,
            timeout=API_TIMEOUT,
            headers={"Content-Type": "application/json"}
        )

        # 解析响应（假设API返回格式：{"code":0,"msg":"success","result":[]}）
        response_data = response.json()
        if response.status_code != 200 or response_data.get("code") != 0:
            raise AppTemplateApiError(f"API调用失败：{response_data.get('msg', '未知错误')}")

        logger.info(f"应用模板API查询成功，返回模板数量：{len(response_data.get('result', []))}")
        return response_data

    except requests.exceptions.Timeout:
        raise AppTemplateApiError("模板查询API超时，请稍后重试")
    except requests.exceptions.ConnectionError:
        raise AppTemplateApiError("模板查询API连接失败，请检查网络")
    except Exception as e:
        raise AppTemplateApiError(f"模板查询异常：{str(e)}")
