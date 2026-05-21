from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from erpguard.product.connector_catalog import ConnectorDefinition
from erpguard.product.models import AutomationDraftModel, DraftReviewModel
from erpguard.product.skill_template_catalog import SkillTemplateDefinition
from erpguard.product.template_installer import InstalledTemplateSummary
from erpguard.product.template_requirements import TemplateRequirementsResult
from erpguard.product.template_safety import TemplateSafetySummary


class ConnectorListResponse(BaseModel):
    connectors: list[ConnectorDefinition] = Field(default_factory=list)


class ConnectorDetailResponse(ConnectorDefinition):
    pass


class SkillTemplateListResponse(BaseModel):
    templates: list[SkillTemplateDefinition] = Field(default_factory=list)


class SkillTemplateDetailResponse(SkillTemplateDefinition):
    safety_summary: TemplateSafetySummary


class TemplateConfigurationRequest(BaseModel):
    configuration: dict[str, Any] = Field(default_factory=dict)


class TemplateRequirementsResponse(TemplateRequirementsResult):
    pass


class TemplateInstallResponse(BaseModel):
    status: str
    template_id: str
    template_name: str
    connector_id: str
    draft: AutomationDraftModel
    review: DraftReviewModel
    requirements: TemplateRequirementsResult
    safety_summary: TemplateSafetySummary
    next_steps: list[str] = Field(default_factory=list)


class InstalledTemplatesResponse(BaseModel):
    installed: list[InstalledTemplateSummary] = Field(default_factory=list)
