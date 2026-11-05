from functools import lru_cache

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")
    database_url: str = "sqlite:///./trading_lab.db"
    cors_origins: list[str] = ["http://localhost:5173"]
    llm_base_url: str = "https://api.openai.com/v1"
    llm_model: str = ""
    llm_api_key: SecretStr = SecretStr("")
    alpaca_api_key: SecretStr = SecretStr("")
    alpaca_secret_key: SecretStr = SecretStr("")
    fred_api_key: SecretStr = SecretStr("")
    benzinga_api_key: SecretStr = SecretStr("")
    worker_poll_seconds: float = 2
    worker_lease_seconds: int = 120
    worker_max_run_seconds: int = 1800
    max_active_jobs: int = 20
    max_dataset_rows: int = 100_000
    max_request_bytes: int = 25_000_000


@lru_cache
def settings() -> Settings:
    return Settings()
