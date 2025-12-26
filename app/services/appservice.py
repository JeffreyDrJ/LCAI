# 查询应用模板
from typing import Dict

import requests
import json

from app.models.schema import LCAIMeta
from app.utils.logger import logger
from app.utils.exceptions import AppTemplateApiError, AppGenerateError

# 第三方API配置
GENERATE_APP_API_URL = "https://eplatdev.baocloud.cn/code-admin/service/S_BE_LA_00"
ACTIVATE_APP_TEMPLATE_API_URL = "https://eplatdev.baocloud.cn/code-admin/service/S_BE_LA_23"
API_TIMEOUT = 60  # 超时时间（秒）


async def generate_app(app_name, meta: Dict) -> Dict:
    """
    调用生成应用API（S_BE_LA_00）
    :param app_name: 应用名称
    :param meta: 元数据（包含userId、origin等环境信息）
    :return: API响应结果
    """
    try:
        # 构造POST请求参数（根据第三方API要求调整，这里假设需要userInput和meta信息）
        request_body = {
            "appName": app_name,
            "appType": "1",
            "spaceId": meta.cur_workspaceId,
            "userId": meta.userId,
            "userName": meta.lcUserName,
            "isApproved": True,
            "isAiCreateApp": True
        }

        # 发送POST请求（同步请求，若需异步可改用aiohttp）
        response = requests.post(
            url=GENERATE_APP_API_URL.replace("https://eplatdev.baocloud.cn", meta.origin),
            json=request_body,
            timeout=API_TIMEOUT,
            headers={"Content-Type": "application/json"}
        )
        response_data = response.json()
        if response_data.get("__sys__").get("status") < 0:
            raise AppGenerateError(f"S_BE_LA_00调用失败：{response_data.get("__sys__").get("msg")}")
        logger.info(f"创建应用API：S_BE_LA_00 执行成功，生成新应用：{response_data.get("appName")}({response_data.get("appId")})")

        return {"app_name": response_data.get("appName"), "app_id": response_data.get("appId")}

    except requests.exceptions.Timeout:
        raise AppGenerateError("创建应用API超时，请稍后重试")
    except requests.exceptions.ConnectionError:
        raise AppGenerateError("创建应用API连接失败，请检查网络")
    except Exception as e:
        raise AppGenerateError(f"创建应用异常：{str(e)}")

async def activate_template(app_name:str, app_template:Dict, meta: LCAIMeta) -> Dict:
    """
    调用生成应用API（S_BE_LA_23）
    :param app_name: 应用名称
    :param app_template_id: 应用模板id
    :param meta: 元数据（包含userId、origin等环境信息）
    :return: API响应结果
    """
    try:
        # 构造POST请求参数（根据第三方API要求调整，这里假设需要userInput和meta信息）
        request_body = {
            "templateId": app_template["templateId"],
            "templateVersion": app_template["templateVersion"],
            "userId": meta.userId,
            "lcUserName": meta.lcUserName,
            "updateApp": False,
            "spaceId": meta.cur_workspaceId,
            "appName": app_name,
            "isApproved": True,
            "isAiCreateApp": True
        }

        # 发送POST请求（同步请求，若需异步可改用aiohttp）
        response = requests.post(
            url=ACTIVATE_APP_TEMPLATE_API_URL.replace("https://eplatdev.baocloud.cn", meta.origin),
            json=request_body,
            timeout=API_TIMEOUT,
            headers={"Content-Type": "application/json"}
        )
        response_data = response.json()
        if response_data.get("__sys__").get("status") < 0:
            raise AppGenerateError(f"S_BE_LA_23调用失败：{response_data.get("__sys__").get("msg")}")
        logger.info(
            f"创建应用API：S_BE_LA_23 执行成功，生成新应用：{app_name}({response_data.get("appId")})")

        return {"app_name": app_name, "app_id": response_data.get("appId")}

    except requests.exceptions.Timeout:
        raise AppGenerateError("应用模板创建应用API超时，请稍后重试")
    except requests.exceptions.ConnectionError:
        raise AppGenerateError("应用模板创建应用API连接失败，请检查网络")
    except Exception as e:
        raise AppGenerateError(f"应用模板创建应用异常：{str(e)}")
