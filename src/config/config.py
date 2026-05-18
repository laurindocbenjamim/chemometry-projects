import os
from pydantic_settings import BaseSettings
from dotenv import load_dotenv

# Resolve absolute path to project root and load .env file explicitly
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
env_path = os.path.join(project_root, ".env")
load_dotenv(dotenv_path=env_path)

class Settings(BaseSettings):
    APP_NAME: str = "Chemometrics API"
    DEBUG: bool = True
    SENTRY_DSN: str = os.getenv("SENTRY_DSN", "")
    ALLOWED_ORIGINS: list = ["*"]
    MAX_FILE_SIZE_MB: int = 5
    
    # GROQ & AI Llama Configuration (Pydantic automatically loads these from .env)
    GROQ_API_KEY: str = ""
    LLMMODEL: str = "llama-3.2-11b-vision-preview"
    LLMPROVIDER: str = "groq"

    class Config:
        env_file = ".env"
        extra = "ignore"

settings = Settings()
