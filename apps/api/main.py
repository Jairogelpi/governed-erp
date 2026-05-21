from fastapi import FastAPI

from apps.api.routes.audit import router as audit_router
from apps.api.routes.connections import router as connections_router
from apps.api.routes.demo import router as demo_router
from apps.api.routes.demo_dashboard import router as demo_dashboard_router
from apps.api.routes.health import router as health_router
from apps.api.routes.product import router as product_router
from apps.api.routes.approval_workflow import router as approval_workflow_router
from apps.api.routes.execution_sandbox import router as execution_sandbox_router
from apps.api.routes.live_read_sandbox import router as live_read_sandbox_router
from apps.api.routes.write_readiness import router as write_readiness_router
from apps.api.routes.write_pilot import router as write_pilot_router
from apps.api.routes.platform_safety import router as platform_safety_router
from apps.api.routes.skill_compilation import router as skill_compilation_router
from apps.api.routes.recordings import router as recordings_router
from apps.api.routes.preflight import router as preflight_router
from apps.api.routes.odoo import router as odoo_router
from apps.api.routes.skills import router as skills_router
from apps.fake_erp.routes import router as fake_erp_router


app = FastAPI(title="ERPGuard API", version="0.1.0")
app.include_router(health_router)
app.include_router(connections_router)
app.include_router(demo_router)
app.include_router(demo_dashboard_router)
app.include_router(recordings_router)
app.include_router(preflight_router)
app.include_router(odoo_router)
app.include_router(product_router)
app.include_router(skill_compilation_router)
app.include_router(approval_workflow_router)
app.include_router(execution_sandbox_router)
app.include_router(live_read_sandbox_router)
app.include_router(write_readiness_router)
app.include_router(write_pilot_router)
app.include_router(platform_safety_router)
app.include_router(audit_router)
app.include_router(skills_router)
app.include_router(fake_erp_router)
