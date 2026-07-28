"""Reserved public execution boundary; raw ERP execution remains unavailable."""

from fastapi import APIRouter


router = APIRouter(prefix="/v1/executions", tags=["executions"])
