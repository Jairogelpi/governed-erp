from fastapi import FastAPI

from apps.api.routes.audit import router as audit_router
from apps.api.routes.connections import router as connections_router
from apps.api.routes.demo import router as demo_router
from apps.api.routes.demo_dashboard import router as demo_dashboard_router
from apps.api.routes.health import router as health_router
from apps.api.routes.product import router as product_router
from apps.api.routes.approval_workflow import router as approval_workflow_router
from apps.api.routes.execution_sandbox import router as execution_sandbox_router
from apps.api.routes.live_read_sandbox import router as live_read_sandbox_router
from apps.api.routes.write_readiness import router as write_readiness_router
from apps.api.routes.write_pilot import router as write_pilot_router
from apps.api.routes.platform_safety import router as platform_safety_router
from apps.api.routes.operator_flow import router as operator_flow_router
from apps.api.routes.r2_write_pilot import router as r2_write_pilot_router
from apps.api.routes.r2_readiness import router as r2_readiness_router
from apps.api.routes.release import router as release_router
from apps.api.routes.marketplace import router as marketplace_router
from apps.api.routes.agent_builder import router as agent_builder_router
from apps.api.routes.agent_builder_advisory import router as agent_builder_advisory_router
from apps.api.routes.agent_proposal_drafts import router as agent_proposal_drafts_router
from apps.api.routes.agent_clarifications import router as agent_clarifications_router
from apps.api.routes.agent_draft_bridge import router as agent_draft_bridge_router
from apps.api.routes.agent_draft_handoff import router as agent_draft_handoff_router
from apps.api.routes.agent_handoff_versioning import router as agent_handoff_versioning_router
from apps.api.routes.agent_candidate_approval import router as agent_candidate_approval_router
from apps.api.routes.agent_candidate_decision import router as agent_candidate_decision_router
from apps.api.routes.agent_candidate_activation_request import router as agent_candidate_activation_request_router
from apps.api.routes.agent_candidate_activation import router as agent_candidate_activation_router
from apps.api.routes.agent_skill_run_preview import router as agent_skill_run_preview_router
from apps.api.routes.semantic_skill_discovery import router as semantic_skill_discovery_router
from apps.api.routes.operator_console import router as operator_console_router
from apps.api.routes.operator_console import alias_router as operator_console_alias_router
from apps.api.routes.connector_auth import router as connector_auth_router
from apps.api.routes.external_connectors import router as external_connectors_router
from apps.api.routes.google_calendar_oauth import router as google_calendar_oauth_router
from apps.api.routes.skill_compilation import router as skill_compilation_router
from apps.api.routes.recordings import router as recordings_router
from apps.api.routes.record_to_skill import router as record_to_skill_router
from apps.api.routes.skill_versioning import router as skill_versioning_router
from apps.api.routes.active_skill_runner import router as active_skill_runner_router
from apps.api.routes.skill_schedules import router as skill_schedules_router
from apps.api.routes.operator_evidence import router as operator_evidence_router
from apps.api.routes.preflight import router as preflight_router
from apps.api.routes.odoo import router as odoo_router
from apps.api.routes.skills import router as skills_router
from apps.fake_erp.routes import router as fake_erp_router


app = FastAPI(title="ERPGuard API", version="0.1.0")
app.include_router(health_router)
app.include_router(connections_router)
app.include_router(demo_router)
app.include_router(demo_dashboard_router)
app.include_router(recordings_router)
app.include_router(preflight_router)
app.include_router(odoo_router)
app.include_router(product_router)
app.include_router(skill_compilation_router)
app.include_router(approval_workflow_router)
app.include_router(execution_sandbox_router)
app.include_router(live_read_sandbox_router)
app.include_router(write_readiness_router)
app.include_router(write_pilot_router)
app.include_router(platform_safety_router)
app.include_router(operator_flow_router)
app.include_router(r2_write_pilot_router)
app.include_router(r2_readiness_router)
app.include_router(release_router)
app.include_router(marketplace_router)
app.include_router(agent_builder_router)
app.include_router(agent_builder_advisory_router)
app.include_router(agent_proposal_drafts_router)
app.include_router(agent_clarifications_router)
app.include_router(agent_draft_bridge_router)
app.include_router(agent_draft_handoff_router)
app.include_router(agent_handoff_versioning_router)
app.include_router(agent_candidate_approval_router)
app.include_router(agent_candidate_decision_router)
app.include_router(agent_candidate_activation_request_router)
app.include_router(agent_candidate_activation_router)
app.include_router(agent_skill_run_preview_router)
app.include_router(semantic_skill_discovery_router)
app.include_router(operator_console_router)
app.include_router(operator_console_alias_router)
app.include_router(connector_auth_router)
app.include_router(external_connectors_router)
app.include_router(google_calendar_oauth_router)
app.include_router(record_to_skill_router)
app.include_router(skill_versioning_router)
app.include_router(active_skill_runner_router)
app.include_router(skill_schedules_router)
app.include_router(operator_evidence_router)
app.include_router(audit_router)
app.include_router(skills_router)
app.include_router(fake_erp_router)
