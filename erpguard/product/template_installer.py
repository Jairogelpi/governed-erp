from __future__ import annotations

import json

from pydantic import BaseModel, Field

from erpguard.db.models import AutomationDraft
from erpguard.db.repositories import (
    create_automation_draft,
    create_business_snapshot,
    create_opportunity,
    create_opportunity_scan,
)
from erpguard.product.draft_review import DraftReviewService
from erpguard.product.models import AutomationDraftModel, DraftReviewModel
from erpguard.product.skill_template_catalog import SkillTemplateCatalogService
from erpguard.product.template_requirements import TemplateRequirementsResult, TemplateRequirementsService
from erpguard.product.template_safety import TemplateSafetyService, TemplateSafetySummary


class InstalledTemplateSummary(BaseModel):
    draft_id: str
    template_id: str
    template_name: str
    connector_id: str
    status: str
    runtime_mode: str
    write_actions: bool = False
    next_step: str = "review"
    created_at: str | None = None


class TemplateInstallResult(BaseModel):
    status: str
    template_id: str
    template_name: str
    connector_id: str
    draft: AutomationDraftModel
    review: DraftReviewModel
    requirements: TemplateRequirementsResult
    safety_summary: TemplateSafetySummary
    next_steps: list[str] = Field(default_factory=list)


class TemplateInstallerService:
    def __init__(self, session) -> None:
        self.session = session

    def install_draft(self, template_id: str, configuration: dict | None = None) -> TemplateInstallResult:
        configuration = configuration or {}
        template = SkillTemplateCatalogService().get_template(template_id)
        if template is None:
            raise ValueError("template_not_found")

        requirements = TemplateRequirementsService().check(template_id, configuration)
        if not requirements.can_install:
            raise ValueError("template_requirements_not_met")

        connection_id = configuration["connection_id"]
        snapshot = create_business_snapshot(
            self.session,
            connection_id=connection_id,
            erp_type=template.connector_id,
            snapshot_json=json.dumps(
                {
                    "source": "marketplace_template",
                    "template_id": template.template_id,
                    "connector_id": template.connector_id,
                    "read_only_mode": True,
                    "configuration_keys": sorted(configuration.keys()),
                },
                default=str,
            ),
            status="marketplace_draft",
            read_only_mode=True,
        )
        scan = create_opportunity_scan(
            self.session,
            business_snapshot_id=snapshot.id,
            connection_id=connection_id,
            status="marketplace_template_selected",
            summary_json=json.dumps({"opportunity_count": 1, "signal_count": 0, "source": "marketplace"}, default=str),
        )
        opportunity = create_opportunity(
            self.session,
            opportunity_scan_id=scan.id,
            connection_id=connection_id,
            code=template.opportunity_code,
            title=template.name,
            description=template.description,
            recommendation="Review, validate, compile, and approve this marketplace draft before activation.",
            category=template.category,
            priority=1,
            signal_codes_json=json.dumps(["marketplace_template"]),
            roi_json=json.dumps(
                {
                    "implementation_effort_hours": 1.0,
                    "estimated_monthly_savings_hours": 0.0,
                    "estimated_monthly_value_eur": 0.0,
                    "payback_weeks": 0.0,
                    "confidence": 0.5,
                    "score": 50,
                    "rationale": "Template selected from internal marketplace; ROI is confirmed during review.",
                },
                default=str,
            ),
            evidence_json=json.dumps({"template_id": template.template_id, "connector_id": template.connector_id}),
            status="marketplace_draft",
        )
        draft_package = {
            "draft_kind": "marketplace_template_draft",
            "marketplace_template_id": template.template_id,
            "connector_id": template.connector_id,
            "runtime_mode": "dry_run_only",
            "write_actions": False,
            "connection_id": connection_id,
            "snapshot_id": snapshot.id,
            "scan_id": scan.id,
            "opportunity_id": opportunity.id,
            "required_guards": template.required_guards,
            "guards": list(dict.fromkeys([*template.required_guards, "no_odoo_writes", "dry_run_only"])),
            "required_permissions": template.required_permissions,
            "configuration": {key: configuration.get(key) for key in template.required_config},
            "steps": [
                {"id": "review_template", "type": "review", "description": "Review marketplace template metadata and requirements."},
                {"id": "check_requirements", "type": "guard", "description": "Confirm connector, permissions, and guards before compilation."},
                {"id": "compile_later", "type": "compile", "description": "Compile through the existing review and approval flow only."},
                {"id": "no_write_execution", "type": "guard", "description": "Keep runtime dry_run_only and write_actions false."},
            ],
        }
        draft_row = create_automation_draft(
            self.session,
            opportunity_id=opportunity.id,
            scan_id=scan.id,
            snapshot_id=snapshot.id,
            connection_id=connection_id,
            name=f"Marketplace Draft - {template.name}",
            description=template.description,
            runtime_mode="dry_run_only",
            write_actions=False,
            draft_json=json.dumps(draft_package, default=str),
            status="marketplace_draft",
        )
        draft_model = self._draft_model(draft_row, draft_package)
        review = DraftReviewService(self.session).get_or_create(draft_row.id)
        safety = TemplateSafetyService().summarize(template)
        return TemplateInstallResult(
            status="draft_installed",
            template_id=template.template_id,
            template_name=template.name,
            connector_id=template.connector_id,
            draft=draft_model,
            review=review,
            requirements=requirements,
            safety_summary=safety,
            next_steps=["review", "validate", "compile", "approval"],
        )

    def list_installed(self) -> list[InstalledTemplateSummary]:
        rows = (
            self.session.query(AutomationDraft)
            .order_by(AutomationDraft.created_at.desc())
            .all()
        )
        installed: list[InstalledTemplateSummary] = []
        for row in rows:
            try:
                package = json.loads(row.draft_json)
            except (TypeError, ValueError):
                continue
            template_id = package.get("marketplace_template_id")
            if not template_id:
                continue
            template = SkillTemplateCatalogService().get_template(template_id)
            installed.append(
                InstalledTemplateSummary(
                    draft_id=row.id,
                    template_id=template_id,
                    template_name=template.name if template else row.name,
                    connector_id=package.get("connector_id", ""),
                    status=row.status,
                    runtime_mode=row.runtime_mode,
                    write_actions=row.write_actions,
                    created_at=row.created_at.isoformat(),
                )
            )
        return installed

    def _draft_model(self, row, package: dict) -> AutomationDraftModel:
        return AutomationDraftModel.model_validate(
            {
                "draft_id": row.id,
                "opportunity_id": row.opportunity_id,
                "scan_id": row.scan_id,
                "snapshot_id": row.snapshot_id,
                "connection_id": row.connection_id,
                "name": row.name,
                "description": row.description,
                "status": row.status,
                "runtime_mode": row.runtime_mode,
                "write_actions": row.write_actions,
                "draft_package": package,
                "created_at": row.created_at.isoformat(),
                "secrets_redacted": True,
            }
        )
