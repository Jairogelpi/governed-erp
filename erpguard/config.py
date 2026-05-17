from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    environment: str = "development"
    database_url: str = "sqlite:///./erpguard.db"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="ERPGUARD_",
        extra="ignore",
    )


settings = Settings()
