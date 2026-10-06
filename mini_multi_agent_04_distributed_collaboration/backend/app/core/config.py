from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

PROJECT_ROOT = Path(__file__).resolve().parents[3]


class Settings(BaseSettings):
    openai_api_key: str = ""
    openai_model: str = "gpt-4.1-mini"
    gemini_api_key: str = ""
    gemini_model: str = "gemini-3.5-flash"
    ollama_base_url: str = "http://127.0.0.1:11434"
    ollama_model: str = "llama3.2"
    gemma_model: str = "gemma3:1b"
    mcp_url: str = "http://127.0.0.1:8010/mcp"
    database_url: str = "postgresql://agent_user:agent_pwd@127.0.0.1:5433/agent_db"
    redis_url: str = "redis://127.0.0.1:6379/0"
    run_ttl_seconds: int = 3600

    model_config = SettingsConfigDict(env_file=PROJECT_ROOT / ".env", env_file_encoding="utf-8", extra="ignore")


settings = Settings()
