from __future__ import annotations

from pydantic import BaseModel, Field

from erpguard.product.connector_catalog import ConnectorCatalogService
from erpguard.product.skill_template_catalog import SkillTemplateCatalogService
from erpguard.product.template_safety import TemplateSafetyService, TemplateSafetySummary


class TemplateRequirementsResult(BaseModel):
    template_id: str
    can_install: bool
    missing_requirements: list[str] = Field(default_factory=list)
    blocking_reasons: list[str] = Field(default_factory=list)
    required_connection: str | None = None
    required_permissions: list[str] = Field(default_factory=list)
    safety_summary: TemplateSafetySummary | None = None


class TemplateRequirementsService:
    def check(self, template_id: str, configuration: dict | None = None) -> TemplateRequirementsResult:
        configuration = configuration or {}
        template = SkillTemplateCatalogService().get_template(template_id)
        if template is None:
            return TemplateRequirementsResult(
                template_id=template_id,
                can_install=False,
                blocking_reasons=["template_not_found"],
            )

        connector = ConnectorCatalogService().get_connector(template.connector_id)
        blocking: list[str] = []
        missing: list[str] = []
        if connector is None:
            blocking.append("connector_not_found")
        elif connector.status != "implemented":
            blocking.append("connector_not_implemented")

        for field in template.required_config:
            if not configuration.get(field):
                missing.append(field)

        if not template.installable:
            blocking.append("template_not_installable")

        return TemplateRequirementsResult(
            template_id=template.template_id,
            can_install=not blocking and not missing,
            missing_requirements=missing,
            blocking_reasons=blocking,
            required_connection=template.required_connection,
            required_permissions=template.required_permissions,
            safety_summary=TemplateSafetyService().summarize(template),
        )
