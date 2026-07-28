"""Install/release diagnostics retained behind the internal-surface flag."""

from fastapi import APIRouter

from apps.api.routes.release import router as release_router


router = APIRouter()
router.include_router(release_router)
