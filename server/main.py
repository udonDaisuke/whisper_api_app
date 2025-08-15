from pathlib import Path

from fastapi import FastAPI
from server.api.routers import router as app_router
from server.api.router_ws import router as app_router_ws
from server.core.config import settings

cache = Path(settings.XDG_CACHE_HOME)
if not cache.exists():
    cache.mkdir(parents=True, exist_ok=True)

app = FastAPI(title="Whisper API",version="0.1.0")
app.include_router(app_router, prefix="/v1")
app.include_router(app_router_ws)  