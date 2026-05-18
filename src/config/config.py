import os
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    APP_NAME: str = "Chemometrics API"
    DEBUG: bool = True
    SENTRY_DSN: str = os.getenv("SENTRY_DSN", "")
    ALLOWED_ORIGINS: list = ["*"]
    MAX_FILE_SIZE_MB: int = 5

    class Config:
        env_file = ".env"

settings = Settings()
