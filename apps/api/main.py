from fastapi import FastAPI

from apps.api.routes.connections import router as connections_router
from apps.api.routes.health import router as health_router
from apps.api.routes.preflight import router as preflight_router


app = FastAPI(title="ERPGuard API", version="0.1.0")
app.include_router(health_router)
app.include_router(connections_router)
app.include_router(preflight_router)
