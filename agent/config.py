from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    # 应用配置
    app_name: str = "工科导航 - 技能测评 Agent"
    app_version: str = "0.1.0"
    debug: bool = True

    # MiniMax API (OpenAI 兼容接口)
    minimax_api_key: str = ""
    minimax_base_url: str = "https://api.minimax.chat/v1"
    minimax_model: str = "MiniMax-M2.7-highspeed"

    # 数据库
    database_url: str = "sqlite:///./skill_agent.db"

    # Redis
    redis_url: str = "redis://localhost:6379/0"

    # JWT 认证
    secret_key: str = "change-me-in-production"
    access_token_expire_minutes: int = 60 * 24 * 7  # 7天

    # 域名（生产环境 CORS 用）
    allowed_domain: str = "localhost"

    # 测评配置
    quick_assessment_questions: int = 20
    deep_assessment_max_turns: int = 15
    score_dimensions: int = 6

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


@lru_cache
def get_settings() -> Settings:
    return Settings()
