from __future__ import annotations

import json

from erpguard.db.repositories import create_automation_draft, create_business_snapshot, create_opportunity, create_opportunity_scan
from erpguard.product.agent_builder_preview import AgentBuilderPreviewService
from erpguard.product.agent_builder_session import AgentBuilderSessionService
from erpguard.product.agent_builder_state import AgentBuilderSaveDraftResult, AgentBuilderSafety
from erpguard.product.agent_builder_validator import AgentBuilderValidator
from erpguard.product.skill_template_catalog import SkillTemplateCatalogService


class AgentBuilderDraftExporter:
    def __init__(self, session) -> None:
        self.session = session

    def save_draft(self, session_id: str) -> AgentBuilderSaveDraftResult:
        validation = AgentBuilderValidator(self.session).validate(session_id)
        if not validation.passed:
            raise ValueError("agent_builder_validation_failed")

        state = AgentBuilderSessionService(self.session).get(session_id)
        preview = AgentBuilderPreviewService(self.session).preview(session_id)
        template = SkillTemplateCatalogService().get_template(state.template_id)
        connection_id = state.inputs.get("connection_id") or "builder_connection_pending"

        snapshot = create_business_snapshot(
            self.session,
            connection_id=connection_id,
            erp_type=state.connector_id or "unknown",
            snapshot_json=json.dumps({"source": "agent_builder", "session_id": session_id, "preview": preview.workflow}, default=str),
            status="agent_builder_draft",
            read_only_mode=True,
        )
        scan = create_opportunity_scan(
            self.session,
            business_snapshot_id=snapshot.id,
            connection_id=connection_id,
            status="agent_builder_ready",
            summary_json=json.dumps({"opportunity_count": 1, "source": "agent_builder"}, default=str),
        )
        opportunity = create_opportunity(
            self.session,
            opportunity_scan_id=scan.id,
            connection_id=connection_id,
            code=template.opportunity_code if template else "agent_builder_custom",
            title=template.name if template else "Agent Builder Draft",
            description=template.description if template else "Safe builder-generated draft.",
            recommendation="Review, validate, compile, and approve this builder draft before activation.",
            category=template.category if template else "agent_builder",
            priority=1,
            signal_codes_json=json.dumps(["agent_builder"]),
            roi_json=json.dumps(
                {
                    "implementation_effort_hours": 1.0,
                    "estimated_monthly_savings_hours": 0.0,
                    "estimated_monthly_value_eur": 0.0,
                    "payback_weeks": 0.0,
                    "confidence": 0.5,
                    "score": 50,
                    "rationale": "Builder draft; ROI reviewed before compile.",
                }
            ),
            evidence_json=json.dumps({"builder_session_id": session_id, "template_id": state.template_id}),
            status="agent_builder_draft",
        )
        draft_package = {
            "draft_kind": "agent_builder_draft",
            "builder_session_id": session_id,
            "marketplace_template_id": state.template_id,
            "connector_id": state.connector_id,
            "runtime_mode": "dry_run_only",
            "write_actions": False,
            "requires_review": True,
            "requires_compile": True,
            "requires_approval": True,
            "guards": list(dict.fromkeys([*state.guards, "no_odoo_writes", "dry_run_only"])),
            "steps": preview.workflow["steps"],
            "workflow_preview": preview.workflow,
        }
        draft = create_automation_draft(
            self.session,
            opportunity_id=opportunity.id,
            scan_id=scan.id,
            snapshot_id=snapshot.id,
            connection_id=connection_id,
            name=f"Agent Builder Draft - {template.name if template else session_id}",
            description=template.description if template else "Safe builder-generated draft.",
            runtime_mode="dry_run_only",
            write_actions=False,
            draft_json=json.dumps(draft_package, default=str),
            status="agent_builder_draft",
        )
        AgentBuilderSessionService(self.session).mark_saved(session_id, draft.id)
        return AgentBuilderSaveDraftResult(
            session_id=session_id,
            status="saved_as_draft",
            automation_draft_id=draft.id,
            runtime_mode="dry_run_only",
            write_actions=False,
            next_step="review_draft",
            safety=AgentBuilderSafety(),
        )
