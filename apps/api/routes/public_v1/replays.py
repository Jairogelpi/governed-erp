"""Reserved public replay boundary; historical replay is explicitly deferred."""

from fastapi import APIRouter


router = APIRouter(prefix="/v1/replays", tags=["replays"])
