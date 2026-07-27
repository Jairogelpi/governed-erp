from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class ProcessRegisterRequest(BaseModel):
    yaml: str = Field(min_length=1)


class ProcessDefinitionResponse(BaseModel):
    id: str
    process_key: str
    version: str
    definition: dict[str, Any]


class ProcessDiffResponse(BaseModel):
    process_key: str
    from_version: str
    to_version: str
    changed: bool
    changed_sections: list[str]
