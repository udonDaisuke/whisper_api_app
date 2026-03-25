from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    WHISPER_MODEL: str = "tiny"
    COMPUTE_DEVICE: str = "cpu"
    COMPUTE_TYPE: str = "int8"
    XDG_CACHE_HOME: str = "/cache"

    class Config:
        env_file = "./env"


settings = Settings()
