from __future__ import annotations

import json
from uuid import uuid4

from erpguard.db.repositories import get_latest_skill_version, get_opportunity
from erpguard.release_ops.models import LiveReadPlanModel, LiveReadStepModel

_FORBIDDEN_REAL_METHODS = {
    "create", "write", "unlink", "copy",
    "action_confirm", "action_done",
    "button_confirm", "button_validate",
}

_STEPS_BY_OPPORTUNITY_CODE: dict[str, list[dict]] = {
    "formula_mapping_alignment": [
        {
            "step_id": "step_01", "odoo_model": "sale.order", "odoo_method": "search_read",
            "fields": ["id", "name", "state", "order_line", "amount_total"],
            "domain": [["state", "in", ["sale", "done"]]], "limit": 5,
            "description": "Load confirmed sales orders to verify formula field alignment",
        },
        {
            "step_id": "step_02", "odoo_model": "sale.order.line", "odoo_method": "search_read",
            "fields": ["id", "order_id", "product_id", "product_uom_qty", "price_unit"],
            "domain": [], "limit": 10,
            "description": "Load order lines to inspect formula field mapping",
        },
    ],
    "read_only_sales_preflight": [
        {
            "step_id": "step_01", "odoo_model": "sale.order", "odoo_method": "search_read",
            "fields": ["id", "name", "state", "amount_total"],
            "domain": [["state", "=", "sale"]], "limit": 5,
            "description": "Load confirmed sales orders for read-only preflight validation",
        },
        {
            "step_id": "step_02", "odoo_model": "sale.order", "odoo_method": "search_count",
            "fields": [], "domain": [["state", "=", "draft"]], "limit": None,
            "description": "Count draft orders pending confirmation",
        },
    ],
    "product_metadata_governance": [
        {
            "step_id": "step_01", "odoo_model": "product.product", "odoo_method": "search_read",
            "fields": ["id", "display_name", "default_code", "tracking", "standard_price"],
            "domain": [], "limit": 5,
            "description": "Load products for metadata governance audit",
        },
        {
            "step_id": "step_02", "odoo_model": "product.template", "odoo_method": "fields_get",
            "fields": ["string", "type"], "domain": [], "limit": None,
            "description": "Inspect product template field definitions",
        },
    ],
}

_DEFAULT_STEPS: list[dict] = [
    {
        "step_id": "step_01", "odoo_model": "sale.order", "odoo_method": "search_read",
        "fields": ["id", "name", "state"], "domain": [], "limit": 3,
        "description": "Load sales orders for live skill execution",
    },
    {
        "step_id": "step_02", "odoo_model": "sale.order", "odoo_method": "search_count",
        "fields": [], "domain": [], "limit": None,
        "description": "Count total available sales orders",
    },
]


def _opportunity_code_matches(code: str, key: str) -> bool:
    return key.lower() in (code or "").lower()


class LiveReadPlanService:
    def __init__(self, session) -> None:
        self.session = session

    def build(self, skill_id: str, connection_id: str | None) -> LiveReadPlanModel:
        version_row = get_latest_skill_version(self.session, skill_id)
        opportunity_code = ""
        if version_row:
            try:
                pkg = json.loads(version_row.skill_package_json)
            except Exception:
                pkg = {}
            opportunity_id = pkg.get("opportunity_id", "")
            if opportunity_id:
                opp = get_opportunity(self.session, opportunity_id)
                if opp:
                    opportunity_code = opp.code

        raw_steps = _DEFAULT_STEPS
        for key, steps in _STEPS_BY_OPPORTUNITY_CODE.items():
            if _opportunity_code_matches(opportunity_code, key):
                raw_steps = steps
                break

        plan_steps: list[LiveReadStepModel] = []
        for s in raw_steps:
            plan_steps.append(
                LiveReadStepModel(
                    step_id=s["step_id"],
                    step_type="real_read",
                    description=s["description"],
                    odoo_model=s["odoo_model"],
                    odoo_method=s["odoo_method"],
                    domain=s.get("domain", []),
                    fields=s.get("fields", []),
                    limit=s.get("limit"),
                    status="pending",
                    real_output=None,
                    write_candidate=None,
                    read_only=True,
                )
            )

        return LiveReadPlanModel(
            plan_id=f"lr_plan_{uuid4().hex[:16]}",
            skill_id=skill_id,
            connection_id=connection_id,
            steps=plan_steps,
            total_steps=len(plan_steps),
            real_read_steps=len(plan_steps),
            blocked_write_candidates=0,
            can_execute_real_writes=False,
            real_erp_writes_enabled=False,
            allow_real_odoo_reads=True,
        )
