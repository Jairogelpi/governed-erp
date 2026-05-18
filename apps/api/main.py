from fastapi import FastAPI

from apps.api.routes.audit import router as audit_router
from apps.api.routes.connections import router as connections_router
from apps.api.routes.demo import router as demo_router
from apps.api.routes.demo_dashboard import router as demo_dashboard_router
from apps.api.routes.health import router as health_router
from apps.api.routes.recordings import router as recordings_router
from apps.api.routes.preflight import router as preflight_router
from apps.api.routes.skills import router as skills_router
from apps.fake_erp.routes import router as fake_erp_router


app = FastAPI(title="ERPGuard API", version="0.1.0")
app.include_router(health_router)
app.include_router(connections_router)
app.include_router(demo_router)
app.include_router(demo_dashboard_router)
app.include_router(recordings_router)
app.include_router(preflight_router)
app.include_router(audit_router)
app.include_router(skills_router)
app.include_router(fake_erp_router)
