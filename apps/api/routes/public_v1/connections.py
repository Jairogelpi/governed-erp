"""Canonical connection paths backed by the unified connection service.

The endpoint implementations remain a temporary compatibility import from
``apps.api.routes.unified_connections``.  The old unified path is retained only
by the explicit legacy app; the replacement owner is this module, deletion wave
C2.
"""

from fastapi import APIRouter

from apps.api.routes.unified_connections import (
    create_unified_connection,
    get_unified_connection,
    list_unified_connections,
)
from apps.api.schemas.unified_connections import UnifiedConnectionResponse


router = APIRouter(prefix="/v1", tags=["connections"])
router.add_api_route(
    "/connections",
    create_unified_connection,
    methods=["POST"],
    response_model=UnifiedConnectionResponse,
    status_code=201,
)
router.add_api_route(
    "/connections",
    list_unified_connections,
    methods=["GET"],
    response_model=list[UnifiedConnectionResponse],
)
router.add_api_route(
    "/connections/{connection_id}",
    get_unified_connection,
    methods=["GET"],
    response_model=UnifiedConnectionResponse,
)
