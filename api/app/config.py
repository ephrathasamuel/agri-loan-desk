"""Settings from environment variables (and api/.env for local runs)."""

import secrets
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # SQLite for simple local runs; docker-compose sets a PostgreSQL URL.
    database_url: str = "sqlite:///./data/agri_loan_desk.db"
    # Signs session tokens. Without one a random key is used, so sign-ins
    # last only until the API restarts.
    secret_key: str = ""
    session_hours: int = 12
    # The first admin account is created from these on start-up when no
    # admin exists yet. Nothing is created if either is empty.
    admin_email: str = ""
    admin_password: str = ""
    admin_name: str = "Administrator"
    anthropic_api_key: str = ""
    # Creates a shared officer account whose sign-in details are shown on the
    # login page, so visitors can try the desk. Off unless set.
    demo_account: bool = False


@lru_cache
def get_settings():
    settings = Settings()
    if not settings.secret_key:
        settings.secret_key = secrets.token_urlsafe(48)
    return settings
