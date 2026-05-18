import os
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    APP_NAME: str = "Chemometrics API"
    DEBUG: bool = True
    SENTRY_DSN: str = os.getenv("SENTRY_DSN", "")
    ALLOWED_ORIGINS: list = ["*"]
    MAX_FILE_SIZE_MB: int = 5
    
    # GROQ & AI Llama Configuration
    GROQ_API_KEY: str = os.getenv("GROQ_API_KEY", "")
    LLMMODEL: str = os.getenv("LLMMODEL", "llama-3.2-11b-vision-preview")
    LLMPROVIDER: str = os.getenv("LLMPROVIDER", "groq")

    class Config:
        env_file = ".env"
        extra = "ignore"

settings = Settings()
