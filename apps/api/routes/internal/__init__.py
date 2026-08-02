"""Opt-in internal tooling composition for the Phase 11.5 app factory."""

from fastapi import APIRouter

from .demo import router as demo_router
from .dev_tokens import router as dev_tokens_router
from .diagnostics import router as diagnostics_router
from .fake_erp import router as fake_erp_router
from .migration import router as migration_router


router = APIRouter()
router.include_router(demo_router)
router.include_router(fake_erp_router)
router.include_router(diagnostics_router)
router.include_router(migration_router)
router.include_router(dev_tokens_router)

__all__ = ["router"]
