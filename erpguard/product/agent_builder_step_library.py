from __future__ import annotations

from pydantic import BaseModel


class AgentBuilderStepDefinition(BaseModel):
    step_type: str
    label: str
    description: str


ALLOWED_STEPS = [
    AgentBuilderStepDefinition(step_type="load_context", label="Load context", description="Load template, connector, and operator inputs."),
    AgentBuilderStepDefinition(step_type="read_record", label="Read record", description="Read one allowed business record through a safe adapter."),
    AgentBuilderStepDefinition(step_type="read_related_records", label="Read related records", description="Read related evidence records without writes."),
    AgentBuilderStepDefinition(step_type="run_guard", label="Run guard", description="Run required ERPGuard policy checks."),
    AgentBuilderStepDefinition(step_type="produce_decision", label="Produce decision", description="Return allow/review/block-style decision evidence."),
    AgentBuilderStepDefinition(step_type="produce_audit_summary", label="Produce audit summary", description="Create an audit-ready summary."),
    AgentBuilderStepDefinition(step_type="create_draft_only", label="Create draft only", description="Prepare draft metadata without execution."),
    AgentBuilderStepDefinition(step_type="blocked_write_candidate", label="Blocked write candidate", description="Represent a blocked write candidate as evidence only."),
]

FORBIDDEN_STEP_TYPES = [
    "raw_execute_kw",
    "python_code",
    "shell_command",
    "browser_click_real_erp",
    "direct_http_request",
    "odoo_create",
    "odoo_write",
    "odoo_unlink",
    "action_confirm",
    "button_validate",
    "action_post",
    "button_mark_done",
]


class AgentBuilderStepLibrary:
    def allowed_steps(self) -> list[AgentBuilderStepDefinition]:
        return list(ALLOWED_STEPS)

    def forbidden_step_types(self) -> list[str]:
        return list(FORBIDDEN_STEP_TYPES)

    def is_allowed(self, step_type: str) -> bool:
        return any(step.step_type == step_type for step in ALLOWED_STEPS)
