"""Reserved public Evidence Pack boundary; legacy audit is not public in C1."""

from fastapi import APIRouter


router = APIRouter(prefix="/v1/evidence", tags=["evidence"])
