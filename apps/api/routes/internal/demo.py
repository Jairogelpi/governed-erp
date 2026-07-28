"""Controlled Fake ERP and Record-to-Skill demo tooling; internal in C1."""

from fastapi import APIRouter

from apps.api.routes.demo import router as full_demo_router
from apps.api.routes.demo_dashboard import router as dashboard_router
from apps.api.routes.record_to_skill import router as record_to_skill_router
from apps.api.routes.recordings import router as recordings_router


router = APIRouter()
router.include_router(full_demo_router)
router.include_router(dashboard_router)
router.include_router(recordings_router)
router.include_router(record_to_skill_router)
