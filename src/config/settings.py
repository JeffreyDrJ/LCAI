# src/config/settings.py
import os
from dotenv import load_dotenv
from pydantic import BaseSettings

# 加载 .env 文件（默认读取项目根目录的 .env）
# 如果 .env 在其他路径，可指定：load_dotenv(dotenv_path="./config/.env")
load_dotenv()


# 进阶：用 Pydantic 封装配置（更规范，支持类型校验）
class Settings(BaseSettings):
    # LLM 配置
    openai_api_key: str = os.getenv("OPENAI_API_KEY")
    llm_model: str = os.getenv("LLM_MODEL", "gpt-3.5-turbo")  # 缺省值
    llm_temperature: float = float(os.getenv("LLM_TEMPERATURE", 0.5))

    # 数据库配置
    db_url: str = os.getenv("DB_URL")

    # 应用配置
    app_env: str = os.getenv("APP_ENV", "development")


# 全局配置实例（其他模块直接导入）
settings = Settings()