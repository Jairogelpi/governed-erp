"""Application composition roots for the public and internal surfaces."""

from __future__ import annotations

import os
from pathlib import Path

from fastapi import FastAPI
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.staticfiles import StaticFiles
from starlette.types import Scope

from apps.api.routes.public_v1 import PUBLIC_ROUTERS
from erpguard.version import __version__

# Spec 94 -- the built React app (`web/dist`, produced by `npm run build`).
# Not committed to the repo, so this is absent in a fresh checkout / most
# unit-test runs; mounting is skipped rather than failing in that case.
WEB_DIST_DIR = Path(__file__).resolve().parents[2] / "web" / "dist"


class _SpaStaticFiles(StaticFiles):
    """Serve `index.html` for client-side routes (`/canary`, `/processes`,
    ...) on a hard refresh or direct link, without masking genuinely
    missing static assets (which always have a file extension)."""

    async def get_response(self, path: str, scope: Scope):
        try:
            return await super().get_response(path, scope)
        except StarletteHTTPException as exc:
            if exc.status_code == 404 and "." not in path.rsplit("/", 1)[-1]:
                return await super().get_response("index.html", scope)
            raise


def _flag(name: str) -> bool:
    return os.getenv(name, "false").strip().lower() in {"1", "true", "yes", "on"}


def create_public_app(*, include_internal: bool | None = None, serve_frontend: bool | None = None) -> FastAPI:
    """Create the default public app with only the declared API roots.

    `serve_frontend` is opt-in and explicit (env `ERPGUARD_SERVE_FRONTEND`,
    default off) rather than inferred from whether `web/dist` happens to
    exist on disk -- callers (tests in particular) must get identical
    behavior regardless of incidental local build artifacts.
    """

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

    should_serve_frontend = serve_frontend if serve_frontend is not None else _flag("ERPGUARD_SERVE_FRONTEND")
    if should_serve_frontend and WEB_DIST_DIR.is_dir():
        # Mounted last: the API routers above are matched first (Starlette
        # checks routes in registration order), so this only ever serves
        # the SPA shell and its static assets, never shadows `/v1/*` or
        # `/internal/*`.
        app.mount("/", _SpaStaticFiles(directory=str(WEB_DIST_DIR), html=True), name="web_app_static")
    return app


def create_app(*, include_internal: bool | None = None, serve_frontend: bool | None = None) -> FastAPI:
    """Build the configured app."""

    return create_public_app(include_internal=include_internal, serve_frontend=serve_frontend)
