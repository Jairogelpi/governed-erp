from __future__ import annotations

import json

from erpguard.db.repositories import create_skill, create_skill_version, create_operator_session
from erpguard.product.platform_tenant import TenantService


_DEMO_SKILL_PACKAGE = {
    "name": "ERPGuard Demo — Formula Review",
    "description": "Controlled demo skill for the operator release candidate walkthrough.",
    "runtime_type": "deterministic_browser",
    "guards": ["no_real_odoo_writes", "formula_check_required"],
    "steps": [
        {"id": "navigate", "type": "navigate", "target": "/fake-erp/sales/orders"},
        {"id": "search_order", "type": "fill", "selector": "[data-testid='order-search']"},
        {"id": "open_order", "type": "click", "selector": "[data-testid='open-order-SO-VALID']"},
        {"id": "check_formula", "type": "evaluate", "guard": "formula_check_required"},
    ],
    "write_actions": False,
    "can_execute_real_writes": False,
    "approved_for_real_execution": False,
}


class DemoSeedService:
    def __init__(self, session) -> None:
        self.session = session

    def seed(self) -> dict:
        tenant = TenantService(self.session).create(
            name="ERPGuard Demo Tenant",
            environment="staging",
        )

        skill = create_skill(
            self.session,
            name=_DEMO_SKILL_PACKAGE["name"],
            description=_DEMO_SKILL_PACKAGE["description"],
        )
        create_skill_version(
            self.session,
            skill_id=skill.id,
            version="1.0.0-demo",
            skill_package_json=json.dumps(_DEMO_SKILL_PACKAGE),
            runtime_type="deterministic_browser",
            llm_required_for_repeated_runs=False,
        )

        session_row = create_operator_session(
            self.session,
            tenant_id=tenant.tenant_id,
            current_step="awaiting_connection",
            known_ids_json=json.dumps({
                "tenant_id": tenant.tenant_id,
                "skill_id": skill.id,
            }),
        )

        return {
            "seeded": True,
            "tenant_id": tenant.tenant_id,
            "tenant_name": tenant.name,
            "tenant_environment": tenant.environment,
            "skill_id": skill.id,
            "skill_name": skill.name,
            "operator_session_id": session_row.id,
            "operator_session_step": session_row.current_step,
            "safety_invariants": {
                "can_execute_real_writes": False,
                "allow_generic_real_odoo_writes": False,
                "allow_r3_r4_real_writes": False,
            },
            "next_steps": [
                "1. Open /demo in your browser",
                "2. Load the operator session in the 'End-to-End Operator Flow' section",
                "3. Select an Odoo connection (or skip for sandbox demo)",
                "4. Click 'Run next step' to advance the operator flow",
                "5. Use the R2 Pilot section to view evidence review and promotion gate",
            ],
        }
