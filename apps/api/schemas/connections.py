from typing import Any

from pydantic import BaseModel


class ConnectionCreateRequest(BaseModel):
    name: str
    erp_type: str
    config: dict[str, Any]


class ConnectionResponse(BaseModel):
    id: str
    name: str
    erp_type: str
    status: str
    config: dict[str, Any]
