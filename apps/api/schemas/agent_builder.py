from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from erpguard.product.agent_builder_state import (
    AgentBuilderEventModel,
    AgentBuilderPreviewModel,
    AgentBuilderSaveDraftResult,
    AgentBuilderSafety,
    AgentBuilderSessionModel,
    AgentBuilderValidationResult,
)
from erpguard.product.agent_builder_step_library import AgentBuilderStepDefinition


class CreateAgentBuilderSessionRequest(BaseModel):
    created_by: dict[str, Any] = Field(default_factory=dict)


class SelectTemplateRequest(BaseModel):
    template_id: str


class SelectConnectorRequest(BaseModel):
    connector_id: str


class ConfigureTriggerRequest(BaseModel):
    trigger: dict[str, Any] = Field(default_factory=dict)


class ConfigureInputsRequest(BaseModel):
    inputs: dict[str, Any] = Field(default_factory=dict)


class ConfigureStepsRequest(BaseModel):
    steps: list[str | dict[str, Any]] = Field(default_factory=list)


class ConfigureGuardsRequest(BaseModel):
    guards: list[str] = Field(default_factory=list)


class AgentBuilderSessionResponse(AgentBuilderSessionModel):
    pass


class AgentBuilderValidationResponse(AgentBuilderValidationResult):
    pass


class AgentBuilderPreviewResponse(AgentBuilderPreviewModel):
    pass


class AgentBuilderSaveDraftResponse(AgentBuilderSaveDraftResult):
    pass


class AgentBuilderTimelineResponse(BaseModel):
    session_id: str
    events: list[AgentBuilderEventModel] = Field(default_factory=list)


class AgentBuilderStepLibraryResponse(BaseModel):
    allowed_steps: list[AgentBuilderStepDefinition] = Field(default_factory=list)
    forbidden_step_types: list[str] = Field(default_factory=list)
    mandatory_guards: list[str] = Field(default_factory=list)
    safety: AgentBuilderSafety = Field(default_factory=AgentBuilderSafety)
