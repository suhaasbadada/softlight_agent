from typing import Optional
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    APP_NAME: str = "Softlight Agent"
    ENV: str = "development"
    GROQ_API_KEY: str
    MODEL_NAME: str

    PLAYWRIGHT_USER_DATA_DIR: Optional[str] = None

    PLAYWRIGHT_STORAGE_STATE: Optional[str] = None

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()