from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    environment: str = "development"
    database_url: str = "sqlite:///./erpguard.db"
    auth_secret: str | None = None
    auth_token_ttl_seconds: int = 900
    local_secret_key: str | None = None
    odoo_confirmation_amount_ceiling: float = 1000.0
    odoo_confirmation_forbidden_marker: str = "ERPGUARD-NO-CONFIRM"
    allow_odoo_governed_confirmation: bool = False
    allow_pricing_scenario_draft: bool = False
    pricing_scenario_max_lines: int = 20
    pricing_scenario_max_total: float = 10000.0
    recommendation_approval_max_age_seconds: int = 86400

    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="ERPGUARD_",
        extra="ignore",
    )


settings = Settings()
