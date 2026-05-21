from __future__ import annotations

import json

from erpguard.core.errors import ObjectNotFoundError
from erpguard.db.repositories import (
    create_automation_draft_review,
    get_automation_draft,
    get_automation_draft_review,
    get_opportunity,
    list_draft_reviews,
)
from erpguard.product.models import (
    DraftGuardModel,
    DraftInputFieldModel,
    DraftOutputFieldModel,
    DraftReviewModel,
    DraftTestCaseModel,
)

_COMMON_GUARDS = [
    DraftGuardModel(name="read_only", description="All Odoo calls are read-only; no create, write, or unlink.", enforced=True),
    DraftGuardModel(name="no_odoo_writes", description="Blocks any Odoo write path at the adapter layer.", enforced=True),
    DraftGuardModel(name="dry_run_only", description="Executes in dry-run mode; no side effects.", enforced=True),
    DraftGuardModel(name="requires_approval_before_activation", description="Cannot be activated for live use without explicit human approval.", enforced=True),
]

_OPPORTUNITY_SCHEMAS: dict[str, dict] = {
    "formula_mapping_alignment": {
        "input": [
            DraftInputFieldModel(name="connection_id", type="str", description="Odoo connection to inspect.", required=True, example="conn_abc123"),
            DraftInputFieldModel(name="capacity_field", type="str", description="Custom capacity field name to verify.", required=True, example="x_studio_capacidad_ml"),
            DraftInputFieldModel(name="formula_model", type="str", description="Custom formula model to verify.", required=True, example="x_sale_formula_line"),
        ],
        "output": [
            DraftOutputFieldModel(name="alignment_status", type="str", description="'aligned' if both field and model confirmed, else 'mismatched'."),
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
            DraftOutputFieldModel(name="fields_filled", type="int", description="Number of key fields with values."),
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

    def get_or_create(self, draft_id: str) -> DraftReviewModel:
        existing = list_draft_reviews(self.session, draft_id)
        if existing:
            row = existing[0]
            return DraftReviewModel.model_validate(
                {
                    "review_id": row.id,
                    "draft_id": row.draft_id,
                    "opportunity_id": row.opportunity_id,
                    "connection_id": row.connection_id,
                    "guards": json.loads(row.guards_json),
                    "input_schema": json.loads(row.input_schema_json),
                    "output_schema": json.loads(row.output_schema_json),
                    "test_cases": json.loads(row.test_cases_json),
                    "status": row.status,
                    "skill_id": row.skill_id,
                    "skill_version_id": row.skill_version_id,
                    "created_at": row.created_at.isoformat(),
                }
            )
        return self.create(draft_id)

    def create(self, draft_id: str) -> DraftReviewModel:
        draft = get_automation_draft(self.session, draft_id)
        if draft is None:
            raise ObjectNotFoundError(f"AutomationDraft '{draft_id}' was not found.")

        opportunity = get_opportunity(self.session, draft.opportunity_id)
        opportunity_code = opportunity.code if opportunity else "generic"

        schema = _OPPORTUNITY_SCHEMAS.get(opportunity_code, _DEFAULT_SCHEMA)
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
                "guards": [g.model_dump() for g in guards],
                "input_schema": [f.model_dump() for f in input_fields],
                "output_schema": [f.model_dump() for f in output_fields],
                "test_cases": [tc.model_dump() for tc in test_cases],
                "status": row.status,
                "skill_id": None,
                "skill_version_id": None,
                "created_at": row.created_at.isoformat(),
            }
        )
