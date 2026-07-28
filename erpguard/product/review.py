from __future__ import annotations

import json

from erpguard.core.errors import ObjectNotFoundError
from erpguard.db.repositories import (
    create_automation_draft_review,
    create_skill,
    create_skill_version,
    get_automation_draft,
    get_automation_draft_review,
    get_opportunity,
    mark_review_compiled,
)
from erpguard.product.models import (
    CompiledSkillModel,
    DraftGuardModel,
    DraftInputFieldModel,
    DraftOutputFieldModel,
    DraftReviewModel,
    DraftTestCaseModel,
)

_COMMON_GUARDS = [
    DraftGuardModel(name="read_only", description="All Odoo calls are read-only; no create, write, or unlink allowed.", enforced=True),
    DraftGuardModel(name="no_odoo_writes", description="Explicitly blocks any Odoo write path at the adapter layer.", enforced=True),
    DraftGuardModel(name="dry_run_only", description="Skill executes in dry-run mode; no side effects are produced.", enforced=True),
    DraftGuardModel(name="requires_approval_before_activation", description="Skill cannot be activated for live use without an explicit human approval step.", enforced=True),
]

_SCHEMAS: dict[str, dict] = {
    "formula_mapping_alignment": {
        "input": [
            DraftInputFieldModel(name="connection_id", type="str", description="Odoo connection to inspect.", required=True, example="conn_abc123"),
            DraftInputFieldModel(name="capacity_field", type="str", description="Custom capacity field name to verify.", required=True, example="x_studio_capacidad_ml"),
            DraftInputFieldModel(name="formula_model", type="str", description="Custom formula model to verify.", required=True, example="x_sale_formula_line"),
        ],
        "output": [
            DraftOutputFieldModel(name="alignment_status", type="str", description="'aligned' if both field and model are confirmed, else 'mismatched'."),
            DraftOutputFieldModel(name="field_found", type="bool", description="True if the capacity field was detected in Odoo."),
            DraftOutputFieldModel(name="model_found", type="bool", description="True if the formula model was detected in Odoo."),
            DraftOutputFieldModel(name="recommendation", type="str", description="Human-readable next action."),
        ],
        "test_cases": [
            DraftTestCaseModel(
                case_id="tc_align_01",
                name="Both field and model present",
                inputs={"connection_id": "conn_demo", "capacity_field": "x_studio_capacidad_ml", "formula_model": "x_sale_formula_line"},
                expected_outcome="alignment_status=aligned, field_found=True, model_found=True",
                expected_decision="allow",
            ),
            DraftTestCaseModel(
                case_id="tc_align_02",
                name="Capacity field missing",
                inputs={"connection_id": "conn_demo", "capacity_field": "x_studio_capacidad_ml", "formula_model": "x_sale_formula_line"},
                expected_outcome="alignment_status=mismatched, field_found=False",
                expected_decision="review_required",
            ),
        ],
    },
    "read_only_sales_preflight": {
        "input": [
            DraftInputFieldModel(name="connection_id", type="str", description="Odoo connection to inspect.", required=True, example="conn_abc123"),
            DraftInputFieldModel(name="order_reference", type="str", description="Sales order reference to inspect.", required=True, example="S00042"),
        ],
        "output": [
            DraftOutputFieldModel(name="preflight_status", type="str", description="'pass', 'warning', or 'block'."),
            DraftOutputFieldModel(name="order_id", type="int", description="Internal Odoo id of the matched sales order."),
            DraftOutputFieldModel(name="line_count", type="int", description="Number of order lines found."),
            DraftOutputFieldModel(name="recommendation", type="str", description="Human-readable next action."),
        ],
        "test_cases": [
            DraftTestCaseModel(
                case_id="tc_sales_01",
                name="Valid sales order",
                inputs={"connection_id": "conn_demo", "order_reference": "S00042"},
                expected_outcome="preflight_status=pass, order_id set",
                expected_decision="allow",
            ),
            DraftTestCaseModel(
                case_id="tc_sales_02",
                name="Order reference not found",
                inputs={"connection_id": "conn_demo", "order_reference": "S99999"},
                expected_outcome="preflight_status=block, order_id=None",
                expected_decision="review_required",
            ),
        ],
    },
    "product_metadata_governance": {
        "input": [
            DraftInputFieldModel(name="connection_id", type="str", description="Odoo connection to inspect.", required=True, example="conn_abc123"),
            DraftInputFieldModel(name="product_ref", type="str", description="Product default_code or display_name to inspect.", required=True, example="PERF100"),
        ],
        "output": [
            DraftOutputFieldModel(name="metadata_status", type="str", description="'complete' or 'incomplete'."),
            DraftOutputFieldModel(name="fields_filled", type="int", description="Number of key fields that have values."),
            DraftOutputFieldModel(name="total_fields", type="int", description="Total key fields checked."),
            DraftOutputFieldModel(name="recommendation", type="str", description="Human-readable next action."),
        ],
        "test_cases": [
            DraftTestCaseModel(
                case_id="tc_prod_01",
                name="Product with complete metadata",
                inputs={"connection_id": "conn_demo", "product_ref": "PERF100"},
                expected_outcome="metadata_status=complete, fields_filled==total_fields",
                expected_decision="allow",
            ),
            DraftTestCaseModel(
                case_id="tc_prod_02",
                name="Product missing key fields",
                inputs={"connection_id": "conn_demo", "product_ref": "UNKNOWN"},
                expected_outcome="metadata_status=incomplete, fields_filled < total_fields",
                expected_decision="review_required",
            ),
        ],
    },
}

_DEFAULT_SCHEMA: dict = {
    "input": [
        DraftInputFieldModel(name="connection_id", type="str", description="Odoo connection to inspect.", required=True, example="conn_abc123"),
        DraftInputFieldModel(name="context", type="dict", description="Additional context for the dry-run.", required=False, example={}),
    ],
    "output": [
        DraftOutputFieldModel(name="status", type="str", description="Outcome status of the dry run."),
        DraftOutputFieldModel(name="recommendation", type="str", description="Human-readable next action."),
    ],
    "test_cases": [
        DraftTestCaseModel(
            case_id="tc_generic_01",
            name="Standard dry-run",
            inputs={"connection_id": "conn_demo", "context": {}},
            expected_outcome="status=review_required",
            expected_decision="review_required",
        ),
    ],
}


class DraftReviewService:
    def __init__(self, session) -> None:
        self.session = session

    def review(self, draft_id: str) -> DraftReviewModel:
        draft = get_automation_draft(self.session, draft_id)
        if draft is None:
            raise ObjectNotFoundError(f"AutomationDraft '{draft_id}' was not found.")

        opportunity = get_opportunity(self.session, draft.opportunity_id)
        opportunity_code = opportunity.code if opportunity else "generic"

        schema = _SCHEMAS.get(opportunity_code, _DEFAULT_SCHEMA)
        guards = list(_COMMON_GUARDS)
        input_fields: list[DraftInputFieldModel] = schema["input"]
        output_fields: list[DraftOutputFieldModel] = schema["output"]
        test_cases: list[DraftTestCaseModel] = schema["test_cases"]

        row = create_automation_draft_review(
            self.session,
            draft_id=draft_id,
            opportunity_id=draft.opportunity_id,
            connection_id=draft.connection_id,
            guards_json=json.dumps([g.model_dump() for g in guards], default=str),
            input_schema_json=json.dumps([f.model_dump() for f in input_fields], default=str),
            output_schema_json=json.dumps([f.model_dump() for f in output_fields], default=str),
            test_cases_json=json.dumps([tc.model_dump() for tc in test_cases], default=str),
            status="ready_to_compile",
        )
        return DraftReviewModel.model_validate(
            {
                "review_id": row.id,
                "draft_id": row.draft_id,
                "opportunity_id": row.opportunity_id,
                "connection_id": row.connection_id,
                "guards": guards,
                "input_schema": input_fields,
                "output_schema": output_fields,
                "test_cases": test_cases,
                "status": row.status,
                "skill_id": None,
                "skill_version_id": None,
                "created_at": row.created_at.isoformat(),
            }
        )


class DraftCompilerService:
    def __init__(self, session) -> None:
        self.session = session

    def compile(self, review_id: str) -> CompiledSkillModel:
        review = get_automation_draft_review(self.session, review_id)
        if review is None:
            raise ObjectNotFoundError(f"DraftReview '{review_id}' was not found.")
        if review.status not in ("ready_to_compile", "compiled"):
            raise ValueError(f"DraftReview '{review_id}' has status '{review.status}' and cannot be compiled.")

        draft = get_automation_draft(self.session, review.draft_id)
        if draft is None:
            raise ObjectNotFoundError(f"AutomationDraft '{review.draft_id}' was not found.")

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
                {"id": "load_review", "type": "review", "description": "Load the draft review and confirm guards are enforced."},
                {"id": "dry_run_inputs", "type": "plan", "description": "Map caller inputs to the input schema."},
                {"id": "guard_check", "type": "guard", "description": "Enforce read_only, no_odoo_writes, dry_run_only."},
                {"id": "dry_run_output", "type": "output", "description": "Produce read-only output matching the output schema."},
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
