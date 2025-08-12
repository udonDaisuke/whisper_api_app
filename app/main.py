from fastapi import FastAPI
from app.api.routers import router as app_router


app = FastAPI(title="Whisper API",version="0.1.0")
app.include_router(app_router, prefix="/v1")


