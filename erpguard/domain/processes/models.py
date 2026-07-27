from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class ProcessModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class ProcessObject(ProcessModel):
    name: str = Field(min_length=1)
    external_types: list[str] = Field(min_length=1)


class ProcessEvent(ProcessModel):
    name: str = Field(min_length=1)
    object: str = Field(min_length=1)


class ProcessDecision(ProcessModel):
    name: str = Field(min_length=1)
    applies_to: str = Field(min_length=1)
    outcomes: list[str] = Field(min_length=1)


class ProcessMetric(ProcessModel):
    name: str = Field(min_length=1)
    kind: str = Field(min_length=1)
    start_event: str | None = None
    end_event: str | None = None
    numerator: str | None = None
    denominator: str | None = None


class ProcessPolicy(ProcessModel):
    name: str = Field(min_length=1)
    decision: str = Field(min_length=1)
    blocking: bool = True


class ProcessFixture(ProcessModel):
    name: str = Field(min_length=1)
    events: list[str] = Field(min_length=1)


class ProcessDefinitionDocument(ProcessModel):
    process_key: str = Field(min_length=1, max_length=128)
    version: str = Field(min_length=1, max_length=64)
    name: str = Field(min_length=1)
    objects: list[ProcessObject] = Field(min_length=1)
    events: list[ProcessEvent] = Field(min_length=1)
    decisions: list[ProcessDecision] = Field(default_factory=list)
    metrics: list[ProcessMetric] = Field(default_factory=list)
    policies: list[ProcessPolicy] = Field(default_factory=list)
    fixtures: list[ProcessFixture] = Field(default_factory=list)
