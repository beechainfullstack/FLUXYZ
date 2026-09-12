from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    twelve_data_api_key: str = ""
    eia_api_key: str = ""
    gemini_api_key: str = ""
    gemini_model: str = "gemini-3.6-flash"
    starrocks_host: str = "127.0.0.1"
    starrocks_port: int = 9030
    starrocks_user: str = "root"
    starrocks_password: str = ""
    starrocks_database: str = "fluxyz"
    allowed_origins: str = "http://localhost:5173"
    ingestion_enabled: bool = True
    poll_seconds: int = 600
    chat_daily_limit: int = 150


settings = Settings()
