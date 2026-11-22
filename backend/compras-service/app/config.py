from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = "postgresql+psycopg://compras:compras@localhost:5432/compras_db"
    events_service_url: str = "http://localhost:8001"
    events_timeout_seconds: float = 0.8

    model_config = {"env_file": ".env"}


settings = Settings()
