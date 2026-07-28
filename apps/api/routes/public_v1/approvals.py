"""Reserved public approval boundary; old product approval routes stay legacy."""

from fastapi import APIRouter


router = APIRouter(prefix="/v1/approvals", tags=["approvals"])
