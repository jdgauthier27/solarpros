from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    model_config = {"env_file": ".env", "env_file_encoding": "utf-8", "extra": "ignore"}

    # App
    app_env: str = "development"
    app_secret_key: str = "change-me-in-production"
    app_base_url: str = "http://localhost:8000"
    frontend_url: str = "http://localhost:3000"
    cors_origins: str = "http://localhost:3000,http://localhost:5173"

    # Database
    database_url: str = "postgresql+asyncpg://solarpros:solarpros@localhost:5432/solarpros"
    database_url_sync: str = "postgresql://solarpros:solarpros@localhost:5432/solarpros"

    # Redis / Celery
    redis_url: str = "redis://localhost:6379/0"
    celery_broker_url: str = "redis://localhost:6379/0"
    celery_result_backend: str = "redis://localhost:6379/1"

    # API Keys
    google_solar_api_key: str = ""
    nrel_api_key: str = ""
    hunter_io_api_key: str = ""
    sendgrid_api_key: str = ""
    anthropic_api_key: str = ""

    # SendGrid
    sendgrid_from_email: str = "solar@yourcompany.com"
    sendgrid_from_name: str = "SolarPros"
    sendgrid_webhook_secret: str = ""

    # Agent Config
    use_mock_scrapers: bool = True
    use_mock_apis: bool = True
    use_mock_solar: bool | None = None   # Override for solar; falls back to use_mock_apis
    use_mock_owner: bool | None = None   # Override for owner; falls back to use_mock_apis

    @property
    def solar_use_mock(self) -> bool:
        return self.use_mock_solar if self.use_mock_solar is not None else self.use_mock_apis

    @property
    def owner_use_mock(self) -> bool:
        return self.use_mock_owner if self.use_mock_owner is not None else self.use_mock_apis

    # CAN-SPAM
    company_physical_address: str = "123 Solar Way, Suite 100, Los Angeles, CA 90001"
    company_name: str = "SolarPros Inc."

    # Rate Limits
    scraping_rate_per_minute: int = 5
    solar_api_rate_per_minute: int = 100
    owner_lookup_rate_per_minute: int = 30
    email_rate_per_hour: int = 100

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",")]


settings = Settings()
