"""Reserved public proof boundary; proof execution is explicitly deferred."""

from fastapi import APIRouter


router = APIRouter(prefix="/v1/proofs", tags=["proofs"])
