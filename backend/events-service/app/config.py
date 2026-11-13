from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = "postgresql+psycopg://events:events@localhost:5432/events_db"

    model_config = {"env_file": ".env"}


settings = Settings()
