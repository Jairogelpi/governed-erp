from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    environment: str = "development"
    database_url: str = "sqlite:///./erpguard.db"
    auth_secret: str | None = None
    auth_token_ttl_seconds: int = 900
    local_secret_key: str | None = None

    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="ERPGUARD_",
        extra="ignore",
    )


settings = Settings()
