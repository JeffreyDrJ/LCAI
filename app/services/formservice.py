# 查询应用模板
from typing import Dict, List

import json
import requests

from app.models.schema import LCAIMeta
from app.utils.logger import logger
from app.utils.exceptions import AppGenerateError, FormModifyError, FormBuildError

# 第三方API配置
GENERATE_FORM_API_URL = "https://eplatdev.baocloud.cn/code-admin/service/S_BE_LV_41"
MODIFY_FORM_API_URL = "https://eplatdev.baocloud.cn/code-admin/service/S_BE_LM_168"
QUERY_FORM_IN_APP_API_URL = "https://eplatdev.baocloud.cn/code-admin/service/S_BE_LV_1101"
QUERY_FORM_VIEW_API_URL = "https://eplatdev.baocloud.cn/code-admin/service/S_BE_LV_10"
API_TIMEOUT = 60  # 超时时间（秒）


async def generate_form(form_name, form_json, app_id, meta: LCAIMeta) -> Dict:
    """
    调用生成应用API（S_BE_LV_41）
    :param form_name: 表单名称
    :param form_json: 表单json
    :param meta: 元数据（包含userId、origin等环境信息）
    :return: API响应结果 model_id
    """
    try:
        # 构造POST请求参数
        request_body = {
            "userId": meta.userId,
            "lcUserName": meta.lcUserName,
            "operateAddr": "",
            "formData": form_json,
            "modelCname": form_name,
            "modelName": "",
            "appId": app_id,
            "workspaceId": meta.cur_workspaceId,
            "description": "",
            "updateMenu": True,
            "addMenu": True
        }

        # 发送POST请求（同步请求，若需异步可改用aiohttp）
        response = requests.post(
            url=GENERATE_FORM_API_URL.replace("https://eplatdev.baocloud.cn", meta.origin),
            json=request_body,
            timeout=API_TIMEOUT,
            headers={"Content-Type": "application/json"}
        )
        response_data = response.json()
        if response_data.get("__sys__").get("status") < 0:
            raise AppGenerateError(f"S_BE_LV_41调用失败：{response_data.get("__sys__").get("msg")}")
        logger.info(
            f"创建表单API：S_BE_LV_41 执行成功，生成新表单：{response_data.get("modelId")}")

        return {"model_id": response_data.get("modelId")}

    except requests.exceptions.Timeout:
        raise FormBuildError("创建表单API超时，请稍后重试")
    except requests.exceptions.ConnectionError:
        raise FormBuildError("创建表单API连接失败，请检查网络")
    except Exception as e:
        raise FormBuildError(f"创建表单异常：{str(e)}")


async def modify_form(model_id, form_modify_json, app_id, meta: LCAIMeta) -> Dict:
    """
    调用生成应用API（S_BE_LM_168）
    :param model_id: 表单id
    :param form_modify_json: 修改表单json（部分字段）
    :param meta: 元数据（包含userId、origin等环境信息）
    :return: API响应结果 model_id
    """
    try:
        # 构造POST请求参数
        request_body = {
            "userId": meta.userId,
            "lcUserName": meta.lcUserName,
            "workspaceId": meta.cur_workspaceId,
            "appId": app_id,
            "modelId": model_id,
            "fieldsJson": form_modify_json
        }

        # 发送POST请求（同步请求，若需异步可改用aiohttp）
        response = requests.post(
            url=MODIFY_FORM_API_URL.replace("https://eplatdev.baocloud.cn", meta.origin),
            json=request_body,
            timeout=API_TIMEOUT,
            headers={"Content-Type": "application/json"}
        )
        response_data = response.json()
        if response_data.get("__sys__").get("status") < 0:
            raise AppGenerateError(f"S_BE_LM_168调用失败：{response_data.get("__sys__").get("msg")}")
        logger.info(f"修改表单API：S_BE_LM_168 执行成功：{response_data.get("modelId")}")

        return {"model_id": response_data.get("modelId"), "form_json":response_data.get("updateFormJson")} #TODO

    except requests.exceptions.Timeout:
        raise FormModifyError("修改表单API超时，请稍后重试")
    except requests.exceptions.ConnectionError:
        raise FormModifyError("修改表单API连接失败，请检查网络")
    except Exception as e:
        raise FormModifyError(f"修改表单异常：{str(e)}")

async def query_form_in_app(app_id:str, meta: LCAIMeta) -> List[Dict]:
    """
    调用API（S_BE_LV_1101）
    :param app_id: 应用id
    :param meta: 元数据（包含userId、origin等环境信息）
    :return: API响应结果 list<map>
    """
    try:
        # 构造POST请求参数
        request_body = {
            "userId": meta.userId,
            "lcUserName": meta.lcUserName,
            "appId": app_id,
            "workspaceId": meta.cur_workspaceId,
            "limit": 5
        }

        # 发送POST请求（同步请求，若需异步可改用aiohttp）
        response = requests.post(
            url=QUERY_FORM_IN_APP_API_URL.replace("https://eplatdev.baocloud.cn", meta.origin),
            json=request_body,
            timeout=API_TIMEOUT,
            headers={"Content-Type": "application/json"}
        )
        response_data = response.json()
        if response_data.get("__sys__").get("status") < 0:
            raise AppGenerateError(f"S_BE_LV_1101调用失败：{response_data.get("__sys__").get("msg")}")
        logger.info(
            f"创建表单API：S_BE_LV_1101 执行成功，查询出实例化表单：{response_data.get("modelList")}")

        return response_data.get("modelList")

    except requests.exceptions.Timeout:
        raise FormBuildError("查询应用内表单API超时，请稍后重试")
    except requests.exceptions.ConnectionError:
        raise FormBuildError("查询应用内表单API连接失败，请检查网络")
    except Exception as e:
        raise FormBuildError(f"查询应用内表单异常：{str(e)}")


async def query_form_view(app_id:str, model_id:str, model_version:str, meta: LCAIMeta) -> Dict:
    """
    调用API（S_BE_LV_10）
    :param app_id: 应用id
    :param meta: 元数据（包含userId、origin等环境信息）
    :return: API响应结果 list<map>
    """
    try:
        # 构造POST请求参数
        request_body = {
            "userId": meta.userId,
            "lcUserName": meta.lcUserName,
            "appId": app_id,
            "workspaceId": meta.cur_workspaceId,
            "modelId": model_id,
            "modelVersion": model_version,
            "querySysFields": True
        }

        # 发送POST请求（同步请求，若需异步可改用aiohttp）
        response = requests.post(
            url=QUERY_FORM_VIEW_API_URL.replace("https://eplatdev.baocloud.cn", meta.origin),
            json=request_body,
            timeout=API_TIMEOUT,
            headers={"Content-Type": "application/json"}
        )
        response_data = response.json()
        if response_data.get("__sys__").get("status") < 0:
            raise AppGenerateError(f"S_BE_LV_10调用失败：{response_data.get("__sys__").get("msg")}")

        logger.info(f"API：S_BE_LV_10 执行成功，查询出表单视图。")
        result = response_data.get("result")
        for view in result:
            if view["Type"] == "form":
                data = view.get("data")
                try:
                    # 将表单视图转换为json格式
                    data = data.replace('\n', '')
                    form_json = json.loads(data)
                    return form_json
                except json.JSONDecodeError as e:
                    logger.error(f"表单JSON解析失败：{str(e)}，json字符串内容：{data}")
                    raise ValueError(f"表单JSON解析失败：{str(e)}")
        return {}

    except requests.exceptions.Timeout:
        raise FormBuildError("查询应用内表单API超时，请稍后重试")
    except requests.exceptions.ConnectionError:
        raise FormBuildError("查询应用内表单API连接失败，请检查网络")
    except Exception as e:
        raise FormBuildError(f"查询应用内表单异常：{str(e)}")