"""C1 compatibility shim; final owner is public_v1 identity, deletion wave C4."""

from apps.api.routes.identity import router

__all__ = ["router"]
