"""Application composition roots for the public and internal surfaces."""

from __future__ import annotations

import os

from fastapi import FastAPI

from apps.api.routes.public_v1 import PUBLIC_ROUTERS
from erpguard.version import __version__


def _flag(name: str) -> bool:
    return os.getenv(name, "false").strip().lower() in {"1", "true", "yes", "on"}


def create_public_app(*, include_internal: bool | None = None) -> FastAPI:
    """Create the default public app with only the declared API roots."""

    app = FastAPI(
        title="ERPGuard API",
        version=__version__,
        docs_url=None,
        redoc_url=None,
        openapi_url=None,
    )
    for router in PUBLIC_ROUTERS:
        app.include_router(router)

    if include_internal if include_internal is not None else _flag("ERPGUARD_INTERNAL_SURFACES"):
        from apps.api.routes.internal import router as internal_router

        app.include_router(internal_router)
    return app


def create_app(*, include_internal: bool | None = None) -> FastAPI:
    """Build the configured app."""

    return create_public_app(include_internal=include_internal)
