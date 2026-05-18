import sentry_sdk
from sentry_sdk.integrations.fastapi import FastApiIntegration
from src.config.config import settings

def init_sentry():
    if settings.SENTRY_DSN:
        sentry_sdk.init(
            dsn=settings.SENTRY_DSN,
            integrations=[FastApiIntegration()],
            traces_sample_rate=1.0,
            profiles_sample_rate=1.0,
        )
        print("Sentry successfully initialized.")
    else:
        print("Sentry DSN not configured, skipping sentry initialization.")
