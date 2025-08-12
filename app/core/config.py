from pydantic_settings import BaseSettings
from pydantic import Field

class Settings(BaseSettings):
    WHISPER_MODEL: str = "small"
    WHISPER_DEVICE: str = "cpu"   # cpu / cuda
    COMPUTE_TYPE: str = "int8"    # cpu:int8 / cuda:float16
    UPLOAD_CHUNK_BYTES: int  =  Field(1 << 20, ge=64 * 1024, le=64 << 20) # 64kb - 64MB:default 1MB
    class Config:
        env_file = ".env"

settings = Settings()
