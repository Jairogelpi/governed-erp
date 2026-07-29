from __future__ import annotations

from fastapi import APIRouter

from apps.api.schemas.release import (
    DemoSeedResponse,
    OperatorSmokeResponse,
    ReleaseHealthResponse,
    ReleaseReadinessResponse,
    SafetyBoundariesResponse,
)
from erpguard.db.session import SessionLocal, init_db
from erpguard.release_ops.demo_seed import DemoSeedService
from erpguard.release_ops.operator_smoke import OperatorSmokeService
from erpguard.release_ops.release_readiness import (
    ReleaseReadinessService,
    _SAFETY_BOUNDARIES,
    _BLOCKED_OPERATIONS,
)
from erpguard.version import __version__

router = APIRouter(prefix="/v1/release", tags=["release"])


@router.get("/health", response_model=ReleaseHealthResponse)
def release_health():
    init_db()
    session = SessionLocal()
    try:
        db_ok = True
        try:
            from erpguard.db.models import Tenant
            session.query(Tenant).count()
        except Exception:
            db_ok = False

        return {
            "status": "ok" if db_ok else "degraded",
            "version": __version__,
            "db_accessible": db_ok,
            "safety_boundaries_locked": all(not v for v in _SAFETY_BOUNDARIES.values()),
            "safety_boundaries": _SAFETY_BOUNDARIES,
        }
    finally:
        session.close()


@router.get("/readiness-report", response_model=ReleaseReadinessResponse)
def readiness_report():
    init_db()
    session = SessionLocal()
    try:
        return ReleaseReadinessService(session).report()
    finally:
        session.close()


@router.post("/demo-seed", response_model=DemoSeedResponse)
def demo_seed():
    init_db()
    session = SessionLocal()
    try:
        return DemoSeedService(session).seed()
    finally:
        session.close()


@router.post("/operator-smoke", response_model=OperatorSmokeResponse)
def operator_smoke():
    init_db()
    session = SessionLocal()
    try:
        return OperatorSmokeService(session).run()
    finally:
        session.close()


@router.get("/safety-boundaries", response_model=SafetyBoundariesResponse)
def safety_boundaries():
    from erpguard.adapters.odoo.pilot_write_client import PILOT_ALLOWED_WRITE_MODELS
    from erpguard.adapters.odoo.r2_write_client import (
        R2_ALLOWED_WRITE_MODELS,
        R2_ALLOWED_WRITE_FIELDS,
    )
    from erpguard.release_ops.r2_write_policy import _ALLOWED_ENVIRONMENTS

    return {
        "safety_boundaries": _SAFETY_BOUNDARIES,
        "blocked_operations": _BLOCKED_OPERATIONS,
        "allowed_r1_models": sorted(PILOT_ALLOWED_WRITE_MODELS),
        "allowed_r2_models": sorted(R2_ALLOWED_WRITE_MODELS),
        "allowed_r2_fields": sorted(R2_ALLOWED_WRITE_FIELDS),
        "allowed_environments": sorted(_ALLOWED_ENVIRONMENTS),
        "notes": [
            "R1 pilot: mail.message.create only. Feature flag off by default.",
            "R2 pilot: res.partner.write on comment/website only. Staging/demo only. Feature flag off by default.",
            "R3/R4 writes: permanently blocked.",
            "Generic writes: permanently blocked.",
            "Double approval required for any write pilot.",
            "Pre/post snapshots captured for all write pilots.",
            "Rollback instructions stored with every write pilot evidence.",
        ],
    }
