from fastapi import FastAPI
from app.api.routers import router as app_router
from app.api.router_ws import router as app_router_ws


app = FastAPI(title="Whisper API",version="0.1.0")
app.include_router(app_router, prefix="/v1")
app.include_router(app_router_ws)  