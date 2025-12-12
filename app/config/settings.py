import os
from dotenv import load_dotenv
from pydantic  import BaseConfig
from loguru import logger

# 加载环境变量
# 加载 .env 文件（默认读取项目根目录的 .env）
# 如果 .env 在其他路径，可指定：load_dotenv(dotenv_path="./config/.env")
load_dotenv()

# 进阶：用 Pydantic 封装配置（更规范，支持类型校验）
class Settings(BaseConfig):
    # LLM 配置 (宝武DS平台配置)
    DS_BASE_URL: str = os.getenv("DS_BASE_URL")
    DS_API_KEY_INTENT: str = os.getenv("DS_API_KEY_INTENT")
    DS_API_KEY_QA: str = os.getenv("DS_API_KEY_QA")
    DS_API_KEY_FORM_BUILD: str = os.getenv("DS_API_KEY_FORM_BUILD")
    DS_API_KEY_FORM_MODIFY: str = os.getenv("DS_API_KEY_FORM_MODIFY")
    DS_MODEL_NAME: str = os.getenv("DS_MODEL_NAME", "qwen-plus")

    # 第三方表单保存API
    FORM_STORAGE_API_URL: str = os.getenv("FORM_STORAGE_API_URL")
    FORM_STORAGE_API_KEY: str = os.getenv("FORM_STORAGE_API_KEY")

    # FastAPI配置
    API_HOST: str = os.getenv("API_HOST", "0.0.0.0")
    API_PORT: int = int(os.getenv("API_PORT", 8000))
    API_CORS_ORIGINS: list = os.getenv("API_CORS_ORIGINS", "*").split(",")

    # 会话配置
    CONTEXT_EXPIRE_TIME: int = int(os.getenv("CONTEXT_EXPIRE_TIME", 3600))

    class Config:
        case_sensitive = True


# 全局配置实例
settings = Settings()


# 验证关键配置
def validate_settings():
    required_keys = [
        "DS_BASE_URL", "DS_API_KEY_INTENT", "DS_API_KEY_QA",
        "DS_API_KEY_FORM_BUILD", "DS_API_KEY_FORM_MODIFY",
        "FORM_STORAGE_API_URL"
    ]
    missing_keys = [key for key in required_keys if not getattr(settings, key)]
    if missing_keys:
        logger.error(f"缺失关键配置：{missing_keys}，请检查.env文件")
        raise ValueError(f"缺失关键配置：{missing_keys}")
    logger.info("配置验证通过")


validate_settings()