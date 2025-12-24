from typing import Dict, Any

from app.models.state import LCAIState
from app.services import formservice
from app.services.ds_platform import ds_client
from app.config.settings import settings
from app.utils.exceptions import FormModifyError
from app.utils.logger import logger
import json

from app.utils.message.views import update_views


class FormModifyAgent:
    """表单修改智能体：根据用户意见修改表单"""
    FORM_NAME_EXTRACT_PROMPT_TEMPLATE = """
    你是表单搭建助手，需要从用户的修改意见中提取出待修改的表单名称。  

    用户意见：{user_input}
    """
    FORM_MODIFY_PROMPT_TEMPLATE = """
    你是低代码表单修改智能助手，请根据用户的修改意见，并以JSONArray返回修改过的组件JSON
    要求：
    1. 仅修改并返回用户意见相关的属性，其他不相关的属性请务必保持一致，不要缺失或更改；
    2. 字段类型仅允许标题（title）、单行文本（input）、多行文本（textarea）、下拉框（select）、日期选择器（date）、多选框组（checkbox）、按钮（button）；
    3. 仅返回JSON格式，不要额外解释
    4. 所涉及的字段对象中均加入一字符串参数“action”，新增则为“insert”,修改则为“modify”,删除则为“delete”
    5. 若用户要求新增一个组件，必须生成新的model属性值！

    现有表单JSON：{form_json}
    用户修改意见：{modify_opinion}
    """

    @classmethod
    async def modify_form(cls, state: LCAIState, modify_opinion: str) -> Dict[str, Any]:
        """
        修改表单结构
        :param form_schema: 原有表单结构
        :param modify_opinion: 用户修改意见
        :return: 修改后的表单结构
        """
        # 1.确认要修改的表单实体
        # 1.1 提取表单名：
        model_id = ""
        original_form_json = {}
        extract_form_name_prompt = cls.FORM_NAME_EXTRACT_PROMPT_TEMPLATE.format(user_input=state.user_input)
        logger.info(f"表单修改智能体处理[待修改表单提取]请求：{state.user_input[:50]}...")
        try:
            response = await ds_client.call_llm(
                api_key=settings.DS_API_KEY_GENERAL_USE,
                chatId=state.meta.chatId,
                prompt=extract_form_name_prompt,
                stream=False,
                temperature=0.1
            )
            form_name = response["content"].strip().lower()
            logger.info(f"表单修改智能体处理[待修改表单提取]提取到表单名：{form_name}")
        except Exception as e:
            logger.error(f"表单名提取提取失败：{str(e)}", exc_info=True)
            raise FormModifyError(f"表单字段要求提取提取失败：{str(e)}")
        # 1.2 首先试图从缓存中找：
        for model_id, view in state.views:
            if view["type"] == "form" and form_name in view["form_name"]:
                model_id = view["model_id"]
                original_form_json = view["list"]
        # 1.3 找不到的话再从空间中查询
        if model_id == "":
            pass
        # TODO

        # 2.生成修改表单JSON：
        modify_form_prompt = cls.FORM_MODIFY_PROMPT_TEMPLATE.format(modify_opinion=modify_opinion, form_json=original_form_json)
        try:
            response = await ds_client.call_llm(
                api_key=settings.DS_API_KEY_FORM_BUILD,
                chatId=state.meta.chatId,
                prompt=modify_form_prompt,
                stream=False,
                temperature=0.1
            )
            modify_json = response["content"].strip().lower()
        except Exception as e:
            logger.error(f"表单修改JSON生成失败：{str(e)}", exc_info=True)
            raise FormModifyError(f"表单修改JSON生成失败：{str(e)}")

        # 3.调用接口更新表单（S_BE_LM_168）
        try:
            response = await formservice.modify_form(
                model_id=model_id,
                form_modify_json=modify_json,
                app_id=state.app_id,
                meta=state.meta
            )
            form_json = response["form_json"];

            logger.info(f"表单修改成功：form_name={form_name}({model_id})，字段数={len(form_json["list"])}")
        except Exception as e:
            logger.error(f"表单修改失败：{str(e)}", exc_info=True)
            raise FormModifyError(f"表单生成失败：{str(e)}")
        # 4.更新表单信息
        views = await update_views(state, model_id, "form", {"form_name": form_name, "list": form_json["list"]})

        # 结果返回
        return {
            "views": views,
        }

# 全局实例
form_modify_agent = FormModifyAgent()