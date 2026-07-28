"""Canonical public health endpoint for the C1 composition root."""

from fastapi import APIRouter


router = APIRouter(prefix="/v1", tags=["health"])


@router.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
