from __future__ import annotations

import json

from erpguard.core.errors import ObjectNotFoundError
from erpguard.db.repositories import (
    create_skill,
    create_skill_version,
    get_automation_draft,
    get_automation_draft_review,
    get_skill,
    get_skill_version,
    mark_review_compiled,
)
from erpguard.product.models import CompiledSkillModel


class SkillPackageBuilder:
    def __init__(self, session) -> None:
        self.session = session

    def build(self, review_id: str) -> CompiledSkillModel:
        review = get_automation_draft_review(self.session, review_id)
        if review is None:
            raise ObjectNotFoundError(f"DraftReview '{review_id}' was not found.")

        draft = get_automation_draft(self.session, review.draft_id)
        if draft is None:
            raise ObjectNotFoundError(f"AutomationDraft '{review.draft_id}' was not found.")

        if review.status == "compiled" and review.skill_id:
            skill_row = get_skill(self.session, review.skill_id)
            version_row = get_skill_version(self.session, review.skill_version_id) if review.skill_version_id else None
            if skill_row and version_row:
                package = json.loads(version_row.skill_package_json)
                return CompiledSkillModel.model_validate(
                    {
                        "skill_id": skill_row.id,
                        "version_id": version_row.id,
                        "draft_id": draft.id,
                        "review_id": review.id,
                        "opportunity_id": draft.opportunity_id,
                        "connection_id": draft.connection_id,
                        "name": skill_row.name,
                        "description": skill_row.description,
                        "runtime_mode": "dry_run_only",
                        "write_actions": False,
                        "requires_approval_before_activation": True,
                        "guards": package.get("guards", []),
                        "input_schema": package.get("input_schema", []),
                        "output_schema": package.get("output_schema", []),
                        "test_cases": package.get("test_cases", []),
                        "created_at": version_row.created_at.isoformat(),
                    }
                )

        guards = json.loads(review.guards_json)
        input_schema = json.loads(review.input_schema_json)
        output_schema = json.loads(review.output_schema_json)
        test_cases = json.loads(review.test_cases_json)

        skill_package = {
            "draft_kind": "compiled_dry_run_skill",
            "runtime_mode": "dry_run_only",
            "write_actions": False,
            "requires_approval_before_activation": True,
            "connection_id": draft.connection_id,
            "draft_id": draft.id,
            "review_id": review.id,
            "opportunity_id": draft.opportunity_id,
            "guards": [g["name"] for g in guards],
            "input_schema": input_schema,
            "output_schema": output_schema,
            "test_cases": test_cases,
            "workflow": [
                {"id": "load_review", "type": "review", "description": "Load the draft review and confirm all guards are enforced."},
                {"id": "map_inputs", "type": "plan", "description": "Map caller inputs against the declared input schema."},
                {"id": "guard_check", "type": "guard", "description": "Enforce read_only, no_odoo_writes, dry_run_only before any data access."},
                {"id": "dry_run_output", "type": "output", "description": "Produce read-only output matching the output schema; no writes emitted."},
            ],
        }

        skill_row = create_skill(
            self.session,
            name=f"Dry-run skill — {draft.name}",
            description=draft.description,
            status="draft",
        )
        version_row = create_skill_version(
            self.session,
            skill_id=skill_row.id,
            version="1.0.0",
            skill_package_json=json.dumps(skill_package, default=str),
            runtime_type="dry_run_only",
            llm_required_for_repeated_runs=False,
        )
        mark_review_compiled(self.session, review_id, skill_row.id, version_row.id)

        return CompiledSkillModel.model_validate(
            {
                "skill_id": skill_row.id,
                "version_id": version_row.id,
                "draft_id": draft.id,
                "review_id": review.id,
                "opportunity_id": draft.opportunity_id,
                "connection_id": draft.connection_id,
                "name": skill_row.name,
                "description": skill_row.description,
                "runtime_mode": "dry_run_only",
                "write_actions": False,
                "requires_approval_before_activation": True,
                "guards": [g["name"] for g in guards],
                "input_schema": input_schema,
                "output_schema": output_schema,
                "test_cases": test_cases,
                "created_at": version_row.created_at.isoformat(),
            }
        )
