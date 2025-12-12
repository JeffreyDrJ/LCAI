from app.services.ds_platform import ds_client
from app.config.settings import settings
from app.utils.logger import logger
from app.models.schema import FormSchema
import json


class FormBuildAgent:
    """表单搭建智能体：生成表单JSON结构"""

    FORM_BUILD_PROMPT_TEMPLATE = """
    你是低代码表单搭建智能助手，请根据用户需求生成标准化的表单JSON结构，严格按照以下格式返回：
    {
      "form_name": "表单名称",
      "description": "表单描述",
      "fields": [
        {
          "field_name": "字段名称",
          "field_type": "字段类型（仅允许：string/number/select/date）",
          "required": true/false,
          "options": ["选项1", "选项2"]（仅select类型需要）,
          "placeholder": "输入提示文字"
        }
      ]
    }

    要求：
    1. 字段类型仅允许string/number/select/date
    2. 合理设置必填项，核心信息必填
    3. 下拉框字段必须提供options列表
    4. 仅返回JSON格式，不要额外解释

    用户需求：{user_input}
    """

    @classmethod
    async def build_form(cls, user_input: str) -> FormSchema:
        """
        生成表单结构
        :param user_input: 用户表单需求
        :return: 标准化表单结构
        """
        prompt = cls.FORM_BUILD_PROMPT_TEMPLATE.format(user_input=user_input)

        logger.info(f"表单搭建智能体处理请求：{user_input[:50]}...")
        response = await ds_client.call_llm(
            api_key=settings.DS_API_KEY_FORM_BUILD,
            prompt=prompt,
            stream=False,
            temperature=0.1
        )

        # 解析表单JSON
        try:
            form_data = json.loads(response["content"])
            form_schema = FormSchema(**form_data)
            logger.info(f"表单生成成功：form_name={form_schema.form_name}，字段数={len(form_schema.fields)}")
            return form_schema
        except json.JSONDecodeError as e:
            logger.error(f"表单JSON解析失败：{str(e)}，响应内容：{response['content']}")
            raise ValueError(f"表单JSON解析失败：{str(e)}")
        except Exception as e:
            logger.error(f"表单结构验证失败：{str(e)}", exc_info=True)
            raise ValueError(f"表单结构验证失败：{str(e)}")


# 全局实例
form_build_agent = FormBuildAgent()