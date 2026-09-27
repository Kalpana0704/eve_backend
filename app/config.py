from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "EVE Healthcare Booking API"
    debug: bool = False

    database_url: str = Field(
        default="postgresql://postgres:postgres@localhost:5432/eve_healthcare",
        validation_alias="DATABASE_URL",
    )

    jwt_secret_key: str = "change-me-in-production-use-openssl-rand"
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_minutes: int = 60 * 24

    # Simulated payment: probability of success (0.0–1.0) when not forced
    payment_success_rate: float = 0.85


settings = Settings()
