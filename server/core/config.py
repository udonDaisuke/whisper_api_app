from pydantic_settings import BaseSettings
from pydantic import Field

class Settings(BaseSettings):
    WHISPER_MODEL: str = "tiny"
    class Config:
        env_file = "./env"

settings = Settings()
