from typing import Any, Dict

from app.models.state import LCAIState
from app.services import generate_new_form
from app.services.ds_platform import ds_client
from app.config.settings import settings
from app.utils.exceptions import FormBuildError
from app.utils.form.form_generate_util import get_form_json_template
from app.utils.logger import logger
from app.models.schema import FormSchema
import json

from app.utils.message.message_manage import push_intermediate_msg


class FormBuildAgent:
    """表单搭建智能体：生成表单JSON结构,并生成表单"""
    FORM_FIELD_REQUIREMENT_PROMPT_TEMPLATE = """
        你是低代码表单搭建智能助手，请根据用户需求提取出表单字段的相关要求，若用户没明确的字段要求就返回空字符串！。
        用户需求：{user_input}
        """

    FORM_JSON_BUILD_PROMPT_TEMPLATE = """
    你是低代码表单搭建智能助手，请根据用户需求生成标准化的表单JSON结构
    要求：
    1. 字段类型仅允许标题（title）、单行文本（input）、多行文本（textarea）、下拉框（select）、日期选择器（date）、多选框组（checkbox）、按钮（button）；
    2. 合理设置必填项，核心信息必填
    3. 下拉框字段必须提供options列表
    4. 仅返回JSON格式，不要额外解释
    5. 请确保生成字段的字段标识（model）,如select_4250rl8d的后8位唯一标识均不一样

    用户需求：
    搭建“{form_name}”表单。{field_requirements}
    """
    model_id = ""
    model_json = {}

    @classmethod
    async def build_form(cls, state: LCAIState, form_name: str, form_prompt: str) -> Dict[str, Any]:
        """
        生成表单
        :param user_input: 用户表单需求
        :return: 表单信息
        """
        # 0.入参初始化
        form_name = form_name if form_name else state.app_name
        form_prompt = form_prompt if form_prompt else state.user_input

        # 1.提取表单搭建需求中的字段要求：
        extract_fr_prompt = cls.FORM_FIELD_REQUIREMENT_PROMPT_TEMPLATE.format(user_input=form_prompt)

        logger.info(f"表单搭建智能体处理[表单字段要求提取]请求：{form_prompt[:50]}...")
        try:
            response = await ds_client.call_llm(
                api_key=settings.DS_API_KEY_GENERAL_USE,
                chatId=state.meta.chatId,
                prompt=extract_fr_prompt,
                stream=False,
                temperature=0.1
            )
            field_requirements = response["content"].strip().lower()
            logger.info(f"表单搭建智能体处理[表单字段要求提取]提取到字段要求：{field_requirements[:50]}...")
        except Exception as e:
            logger.error(f"表单字段要求提取提取失败：{str(e)}", exc_info=True)
            raise FormBuildError(f"表单字段要求提取提取失败：{str(e)}")
        # 2.生成表单JSON：
        prompt = cls.FORM_JSON_BUILD_PROMPT_TEMPLATE.format(form_name=form_name, field_requirements=field_requirements)

        logger.info(f"表单搭建智能体处理请求：[表单JSON生成]...")
        try:
            response = await ds_client.call_llm(
                api_key=settings.DS_API_KEY_FORM_BUILD,
                chatId=state.meta.chatId,
                prompt=prompt,
                stream=False,
                temperature=0.1
            )
            list_str = response["content"].strip().lower()
        except Exception as e:
            logger.error(f"表单JSON生成失败：{str(e)}", exc_info=True)
            raise FormBuildError(f"表单JSON生成失败：{str(e)}")
        # 3.解析校验表单JSON：
        form_json = get_form_json_template()
        try:
            # 处理AI生成的表单字段内容
            list_str = list_str.replace('\n','')
            list = json.loads(list_str)
            form_json["list"] = list
            model_json = form_json
        except json.JSONDecodeError as e:
            logger.error(f"表单JSON解析失败：{str(e)}，生成的表单list内容：{list_str}")
            raise ValueError(f"表单JSON解析失败：{str(e)}")
        except Exception as e:
            logger.error(f"表单JSON生成失败：{str(e)}", exc_info=True)
            raise ValueError(f"表单JSON生成失败：{str(e)}")
        state = await push_intermediate_msg(state, "表单设计完成，正在初始化...")
        # 4.调用S_BE接口：
        try:
            response = await generate_new_form.generate_form(
                form_name=form_name,
                form_json=form_json,
                app_id=state.app_id,
                meta=state.meta
            )

            model_id = response["model_id"];

            logger.info(f"表单生成成功：form_name={form_name}({model_id})，字段数={len(model_json["list"])}")

            return {
                "model_id": model_id,
                "form_name": form_name
            }

        except Exception as e:
            logger.error(f"表单生成失败：{str(e)}", exc_info=True)
            raise FormBuildError(f"表单生成失败：{str(e)}")

# 全局实例
form_build_agent = FormBuildAgent()
