from __future__ import annotations

from erpguard.core.errors import ObjectNotFoundError
from erpguard.product.agent_builder_session import AgentBuilderSessionService
from erpguard.product.agent_builder_state import (
    MANDATORY_GUARDS,
    ODOO_FORMULA_GUARDS,
    WRITE_PILOT_GUARDS,
    AgentBuilderValidationIssue,
    AgentBuilderValidationResult,
)
from erpguard.product.agent_builder_step_library import AgentBuilderStepLibrary
from erpguard.product.connector_catalog import ConnectorCatalogService
from erpguard.product.skill_template_catalog import SkillTemplateCatalogService
from erpguard.product.template_requirements import TemplateRequirementsService


class AgentBuilderValidator:
    def __init__(self, session) -> None:
        self.session = session

    def validate(self, session_id: str) -> AgentBuilderValidationResult:
        try:
            state = AgentBuilderSessionService(self.session).get(session_id)
        except ObjectNotFoundError:
            return AgentBuilderValidationResult(
                session_id=session_id,
                passed=False,
                issues=[AgentBuilderValidationIssue(code="session_not_found", message=f"Builder session '{session_id}' was not found.")],
            )

        issues: list[AgentBuilderValidationIssue] = []
        if not state.template_id:
            issues.append(AgentBuilderValidationIssue(code="template_missing", message="Select a marketplace template."))
        if not state.connector_id:
            issues.append(AgentBuilderValidationIssue(code="connector_missing", message="Select a connector."))

        template = SkillTemplateCatalogService().get_template(state.template_id) if state.template_id else None
        connector = ConnectorCatalogService().get_connector(state.connector_id) if state.connector_id else None
        if state.template_id and template is None:
            issues.append(AgentBuilderValidationIssue(code="template_not_found", message=f"Template '{state.template_id}' was not found."))
        if state.connector_id and connector is None:
            issues.append(AgentBuilderValidationIssue(code="connector_not_found", message=f"Connector '{state.connector_id}' was not found."))
        if template and connector and template.connector_id != connector.connector_id:
            issues.append(AgentBuilderValidationIssue(code="connector_template_mismatch", message="Selected connector does not match selected template."))

        library = AgentBuilderStepLibrary()
        for step in state.steps:
            step_type = step.get("type", "")
            if step_type in library.forbidden_step_types() or not library.is_allowed(step_type):
                issues.append(AgentBuilderValidationIssue(code="forbidden_step_type", message=f"Step type '{step_type}' is not allowed."))

        required_guards = list(MANDATORY_GUARDS)
        if template and "formula" in template.template_id:
            required_guards.extend(ODOO_FORMULA_GUARDS)
        if template and "write" in template.template_id:
            required_guards.extend(WRITE_PILOT_GUARDS)
        for guard in dict.fromkeys(required_guards):
            if guard not in state.guards:
                issues.append(AgentBuilderValidationIssue(code="missing_mandatory_guard", message=f"Missing guard '{guard}'."))

        if template:
            requirement_result = TemplateRequirementsService().check(template.template_id, state.inputs)
            if not requirement_result.can_install:
                issues.append(AgentBuilderValidationIssue(code="template_requirements_failed", message="Marketplace template requirements are not met."))

        return AgentBuilderValidationResult(session_id=session_id, passed=len(issues) == 0, issues=issues)
