from __future__ import annotations

from erpguard.product.agent_builder_session import AgentBuilderSessionService
from erpguard.product.agent_builder_state import AgentBuilderPreviewModel, AgentBuilderSafety


class AgentBuilderPreviewService:
    def __init__(self, session) -> None:
        self.session = session

    def preview(self, session_id: str) -> AgentBuilderPreviewModel:
        state = AgentBuilderSessionService(self.session).get(session_id)
        workflow = {
            "builder_session_id": session_id,
            "template_id": state.template_id,
            "connector_id": state.connector_id,
            "trigger": state.trigger,
            "inputs": state.inputs,
            "steps": state.steps,
            "guards": state.guards,
            "runtime_mode": "dry_run_only",
            "write_actions": False,
            "requires_review": True,
            "requires_compile": True,
            "requires_approval": True,
        }
        preview = AgentBuilderPreviewModel(
            session_id=session_id,
            status="safety_previewed",
            runtime_mode="dry_run_only",
            write_actions=False,
            workflow=workflow,
            safety=AgentBuilderSafety(),
        )
        AgentBuilderSessionService(self.session).set_preview(session_id, preview.model_dump(mode="json"))
        return preview
