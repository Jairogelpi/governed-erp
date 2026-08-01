from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class CanaryModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class RoutingContext(CanaryModel):
    business_object_key: str
    object_type: str | None = None
    company_id: int | None = None
    capability: str | None = None
    amount: str | None = None
