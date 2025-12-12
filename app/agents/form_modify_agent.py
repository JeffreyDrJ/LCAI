from app.services.ds_platform import ds_client
from app.config.settings import settings
from app.utils.logger import logger
from app.models.schema import FormSchema
import json


class FormModifyAgent:
    """表单修改智能体：根据用户意见修改表单"""

    FORM_MODIFY_PROMPT_TEMPLATE = """
    你是低代码表单修改智能助手，请根据用户的修改意见，更新现有表单结构，严格按照以下格式返回：
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
    1. 仅修改用户指定的部分，保留其他原有字段和配置
    2. 字段类型仅允许string/number/select/date
    3. 仅返回JSON格式，不要额外解释

    现有表单：{form_json}
    用户修改意见：{modify_opinion}
    """

    @classmethod
    async def modify_form(cls, form_schema: FormSchema, modify_opinion: str) -> FormSchema:
        """
        修改表单结构
        :param form_schema: 原有表单结构
        :param modify_opinion: 用户修改意见
        :return: 修改后的表单结构
        """
        form_json = json.dumps(form_schema.model_dump(), ensure_ascii=False)
        prompt = cls.FORM_MODIFY_PROMPT_TEMPLATE.format(
            form_json=form_json,
            modify_opinion=modify_opinion
        )

        logger.info(f"表单修改智能体处理请求：{modify_opinion[:50]}...")
        response = await ds_client.call_llm(
            api_key=settings.DS_API_KEY_FORM_MODIFY,
            prompt=prompt,
            stream=False,
            temperature=0.1
        )

        # 解析修改后的表单JSON
        try:
            form_data = json.loads(response["content"])
            new_form_schema = FormSchema(**form_data)
            logger.info(f"表单修改成功：form_name={new_form_schema.form_name}，字段数={len(new_form_schema.fields)}")
            return new_form_schema
        except json.JSONDecodeError as e:
            logger.error(f"修改后表单JSON解析失败：{str(e)}，响应内容：{response['content']}")
            raise ValueError(f"修改后表单JSON解析失败：{str(e)}")
        except Exception as e:
            logger.error(f"修改后表单结构验证失败：{str(e)}", exc_info=True)
            raise ValueError(f"修改后表单结构验证失败：{str(e)}")


# 全局实例
form_modify_agent = FormModifyAgent()