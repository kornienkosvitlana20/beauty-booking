import os


class Settings:
    database_url: str = os.getenv("DATABASE_URL", "sqlite:///./beauty.db")
    secret_key: str = os.getenv("SECRET_KEY", "dev-secret-change-me")
    token_ttl_minutes: int = int(os.getenv("TOKEN_TTL_MINUTES", "120"))
    slot_step_minutes: int = 30


settings = Settings()
