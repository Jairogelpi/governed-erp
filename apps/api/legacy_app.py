"""Explicit legacy composition.

This module preserves the pre-C1 route composition for a temporary migration
window.  It is never mounted by default; the replacement is
``apps.api.app_factory.create_public_app`` and the deletion wave is C6.
"""

from __future__ import annotations

import importlib

from fastapi import FastAPI

from erpguard.version import __version__


_ROUTER_IMPORTS = (
    ("apps.api.routes.health", "router"),
    ("apps.api.routes.identity", "router"),
    ("apps.api.routes.connections", "router"),
    ("apps.api.routes.unified_connections", "router"),
    ("apps.api.routes.public_v1.events", "router"),
    ("apps.api.routes.processes", "router"),
    ("apps.api.routes.public_v1.variants", "router"),
    ("apps.api.routes.public_v1.candidates", "router"),
    ("apps.api.routes.demo", "router"),
    ("apps.api.routes.demo_dashboard", "router"),
    ("apps.api.routes.recordings", "router"),
    ("apps.api.routes.preflight", "router"),
    ("apps.api.routes.odoo", "router"),
    ("apps.api.routes.product", "router"),
    ("apps.api.routes.skill_compilation", "router"),
    ("apps.api.routes.approval_workflow", "router"),
    ("apps.api.routes.execution_sandbox", "router"),
    ("apps.api.routes.live_read_sandbox", "router"),
    ("apps.api.routes.write_readiness", "router"),
    ("apps.api.routes.write_pilot", "router"),
    ("apps.api.routes.platform_safety", "router"),
    ("apps.api.routes.operator_flow", "router"),
    ("apps.api.routes.r2_write_pilot", "router"),
    ("apps.api.routes.r2_readiness", "router"),
    ("apps.api.routes.release", "router"),
    ("apps.api.routes.marketplace", "router"),
    ("apps.api.routes.agent_builder", "router"),
    ("apps.api.routes.agent_builder_advisory", "router"),
    ("apps.api.routes.agent_proposal_drafts", "router"),
    ("apps.api.routes.agent_clarifications", "router"),
    ("apps.api.routes.agent_draft_bridge", "router"),
    ("apps.api.routes.agent_draft_handoff", "router"),
    ("apps.api.routes.agent_handoff_versioning", "router"),
    ("apps.api.routes.agent_candidate_approval", "router"),
    ("apps.api.routes.agent_candidate_decision", "router"),
    ("apps.api.routes.agent_candidate_activation_request", "router"),
    ("apps.api.routes.agent_candidate_activation", "router"),
    ("apps.api.routes.agent_skill_run_preview", "router"),
    ("apps.api.routes.semantic_skill_discovery", "router"),
    ("apps.api.routes.operator_console", "router"),
    ("apps.api.routes.operator_console", "alias_router"),
    ("apps.api.routes.operator_action_plan", "router"),
    ("apps.api.routes.operator_action_dispatch", "router"),
    ("apps.api.routes.operator_action_dispatch_execute", "router"),
    ("apps.api.routes.manual_dry_run", "router"),
    ("apps.api.routes.fake_erp_execution", "router"),
    ("apps.api.routes.fake_erp_evidence_pack", "router"),
    ("apps.api.routes.fake_erp_regression", "router"),
    ("apps.api.routes.erp_adapter_capability", "router"),
    ("apps.api.routes.erp_adapter_policy", "router"),
    ("apps.api.routes.connector_setup", "router"),
    ("apps.api.routes.connector_auth", "router"),
    ("apps.api.routes.connector_credentials", "router"),
    ("apps.api.routes.erp_fingerprinting", "router"),
    ("apps.api.routes.safe_discovery", "router"),
    ("apps.api.routes.generated_capabilities", "router"),
    ("apps.api.routes.read_only_connector_activation", "router"),
    ("apps.api.routes.odoo_read_only_adapter", "router"),
    ("apps.api.routes.odoo_connection_test", "router"),
    ("apps.api.routes.odoo_read_mapping", "router"),
    ("apps.api.routes.odoo_read_evidence", "router"),
    ("apps.api.routes.odoo_read_only_demo", "router"),
    ("apps.api.routes.visual_browser_session", "router"),
    ("apps.api.routes.visual_observation", "router"),
    ("apps.api.routes.visual_workflow_trace", "router"),
    ("apps.api.routes.visual_table_form_extraction", "router"),
    ("apps.api.routes.external_connectors", "router"),
    ("apps.api.routes.google_calendar_oauth", "router"),
    ("apps.api.routes.record_to_skill", "router"),
    ("apps.api.routes.skill_versioning", "router"),
    ("apps.api.routes.active_skill_runner", "router"),
    ("apps.api.routes.skill_schedules", "router"),
    ("apps.api.routes.operator_evidence", "router"),
    ("apps.api.routes.audit", "router"),
    ("apps.api.routes.skills", "router"),
    ("apps.fake_erp.routes", "router"),
)


def create_legacy_app() -> FastAPI:
    app = FastAPI(title="ERPGuard API (legacy)", version=__version__)
    for module_name, attribute in _ROUTER_IMPORTS:
        router = getattr(importlib.import_module(module_name), attribute)
        app.include_router(router)
    return app
