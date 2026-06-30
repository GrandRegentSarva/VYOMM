from functools import lru_cache

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    app_name: str = "VYOMM Predictive NOC Copilot"
    sqlite_path: str = "/data/vyomm.db"
    groq_api_key: str = "demo-mode"
    groq_base_url: str = "https://api.groq.com/openai/v1"
    groq_model: str = "llama-3.3-70b-versatile"
    chroma_host: str = "chromadb"
    chroma_port: int = 8000
    runbook_path: str = "/app/runbooks"


@lru_cache
def get_settings() -> Settings:
    return Settings()
