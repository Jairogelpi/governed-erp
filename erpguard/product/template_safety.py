from __future__ import annotations

from pydantic import BaseModel, Field

from erpguard.product.skill_template_catalog import SkillTemplateDefinition


class TemplateSafetySummary(BaseModel):
    template_id: str
    risk_level: str
    can_install_as_draft: bool
    write_actions_enabled: bool = False
    generic_writes_enabled: bool = False
    r3_r4_enabled: bool = False
    requires_review_compile_approval: bool = True
    guards: list[str] = Field(default_factory=list)
    safety_notes: list[str] = Field(default_factory=list)


class TemplateSafetyService:
    def summarize(self, template: SkillTemplateDefinition) -> TemplateSafetySummary:
        guards = list(dict.fromkeys([*template.required_guards, "requires_approval_before_activation"]))
        return TemplateSafetySummary(
            template_id=template.template_id,
            risk_level=template.risk_level,
            can_install_as_draft=template.installable,
            write_actions_enabled=False,
            generic_writes_enabled=False,
            r3_r4_enabled=False,
            requires_review_compile_approval=True,
            guards=guards,
            safety_notes=[
                "Template installs only as an automation draft.",
                "Existing review, validation, compile, and approval gates remain mandatory.",
                "No generic writes or R3/R4 writes are enabled.",
                *template.notes,
            ],
        )
