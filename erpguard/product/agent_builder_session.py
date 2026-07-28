from __future__ import annotations

import json

from erpguard.core.errors import ObjectNotFoundError
from erpguard.db.repositories import (
    create_agent_builder_event,
    create_agent_builder_session,
    get_agent_builder_session,
    list_agent_builder_events,
    update_agent_builder_session,
)
from erpguard.product.agent_builder_state import AgentBuilderEventModel, AgentBuilderSafety, AgentBuilderSessionModel
from erpguard.product.agent_builder_step_library import AgentBuilderStepLibrary


_NEXT_STEP = {
    "created": "select_template",
    "template_selected": "select_connector",
    "connector_selected": "configure_trigger",
    "trigger_configured": "configure_inputs",
    "inputs_configured": "configure_steps",
    "steps_configured": "configure_guards",
    "guards_configured": "check_requirements",
    "requirements_checked": "preview",
    "safety_previewed": "save_draft",
    "ready_to_save_draft": "save_draft",
    "saved_as_draft": "review_draft",
}


class AgentBuilderSessionService:
    def __init__(self, session) -> None:
        self.session = session

    def create(self, created_by: dict) -> AgentBuilderSessionModel:
        row = create_agent_builder_session(self.session, json.dumps(created_by, default=str))
        self._event(row.id, "session_created", {}, {"status": row.status})
        return self._model(row)

    def get(self, session_id: str) -> AgentBuilderSessionModel:
        row = self._row(session_id)
        return self._model(row)

    def select_template(self, session_id: str, template_id: str) -> AgentBuilderSessionModel:
        row = update_agent_builder_session(self.session, session_id, template_id=template_id, status="template_selected")
        self._event(session_id, "template_selected", {"template_id": template_id}, {"status": "template_selected"})
        return self._model(row)

    def select_connector(self, session_id: str, connector_id: str) -> AgentBuilderSessionModel:
        row = update_agent_builder_session(self.session, session_id, connector_id=connector_id, status="connector_selected")
        self._event(session_id, "connector_selected", {"connector_id": connector_id}, {"status": "connector_selected"})
        return self._model(row)

    def configure_trigger(self, session_id: str, trigger: dict) -> AgentBuilderSessionModel:
        row = update_agent_builder_session(self.session, session_id, trigger_json=json.dumps(trigger, default=str), status="trigger_configured")
        self._event(session_id, "trigger_configured", trigger, {"status": "trigger_configured"})
        return self._model(row)

    def configure_inputs(self, session_id: str, inputs: dict) -> AgentBuilderSessionModel:
        row = update_agent_builder_session(self.session, session_id, inputs_json=json.dumps(inputs, default=str), status="inputs_configured")
        self._event(session_id, "inputs_configured", inputs, {"status": "inputs_configured"})
        return self._model(row)

    def configure_steps(self, session_id: str, steps: list[str | dict]) -> AgentBuilderSessionModel:
        normalized: list[dict] = []
        library = AgentBuilderStepLibrary()
        for item in steps:
            step_type = str(item.get("type", "")) if isinstance(item, dict) else str(item)
            normalized.append({"id": f"step_{len(normalized) + 1}", "type": step_type, "allowed": library.is_allowed(step_type)})
        row = update_agent_builder_session(self.session, session_id, steps_json=json.dumps(normalized, default=str), status="steps_configured")
        self._event(session_id, "steps_configured", {"steps": normalized}, {"status": "steps_configured"})
        return self._model(row)

    def configure_guards(self, session_id: str, guards: list[str]) -> AgentBuilderSessionModel:
        row = update_agent_builder_session(self.session, session_id, guards_json=json.dumps(guards, default=str), status="guards_configured")
        self._event(session_id, "guards_configured", {"guards": guards}, {"status": "guards_configured"})
        return self._model(row)

    def set_requirement_result(self, session_id: str, result: dict) -> AgentBuilderSessionModel:
        row = update_agent_builder_session(self.session, session_id, requirement_result_json=json.dumps(result, default=str), status="requirements_checked")
        self._event(session_id, "requirements_checked", {}, result)
        return self._model(row)

    def set_preview(self, session_id: str, preview: dict) -> AgentBuilderSessionModel:
        row = update_agent_builder_session(self.session, session_id, safety_preview_json=json.dumps(preview, default=str), status="safety_previewed")
        self._event(session_id, "safety_previewed", {}, preview)
        return self._model(row)

    def mark_saved(self, session_id: str, draft_id: str) -> AgentBuilderSessionModel:
        row = update_agent_builder_session(self.session, session_id, automation_draft_id=draft_id, status="saved_as_draft")
        self._event(session_id, "draft_saved", {}, {"automation_draft_id": draft_id})
        return self._model(row)

    def check_requirements(self, session_id: str):
        from erpguard.product.agent_builder_validator import AgentBuilderValidator

        result = AgentBuilderValidator(self.session).validate(session_id)
        self.set_requirement_result(session_id, result.model_dump(mode="json"))
        return result

    def timeline(self, session_id: str) -> list[AgentBuilderEventModel]:
        return [self._event_model(row) for row in list_agent_builder_events(self.session, session_id)]

    def _row(self, session_id: str):
        row = get_agent_builder_session(self.session, session_id)
        if row is None:
            raise ObjectNotFoundError(f"AgentBuilderSession '{session_id}' was not found.")
        return row

    def _event(self, session_id: str, event_type: str, input_value: dict, output_value: dict, status: str = "ok") -> None:
        create_agent_builder_event(
            self.session,
            session_id=session_id,
            event_type=event_type,
            status=status,
            input_json=json.dumps(input_value, default=str),
            output_json=json.dumps(output_value, default=str),
            error_json="{}",
        )

    def _model(self, row) -> AgentBuilderSessionModel:
        return AgentBuilderSessionModel(
            session_id=row.id,
            status=row.status,
            next_step=_NEXT_STEP.get(row.status, "select_template"),
            template_id=row.template_id,
            connector_id=row.connector_id,
            trigger=json.loads(row.trigger_json or "{}"),
            inputs=json.loads(row.inputs_json or "{}"),
            outputs=json.loads(row.outputs_json or "{}"),
            steps=json.loads(row.steps_json or "[]"),
            guards=json.loads(row.guards_json or "[]"),
            requirement_result=json.loads(row.requirement_result_json or "{}"),
            safety_preview=json.loads(row.safety_preview_json or "{}"),
            automation_draft_id=row.automation_draft_id,
            created_by=json.loads(row.created_by_actor_json or "{}"),
            safety=AgentBuilderSafety(),
            created_at=row.created_at.isoformat(),
            updated_at=row.updated_at.isoformat() if row.updated_at else None,
        )

    def _event_model(self, row) -> AgentBuilderEventModel:
        return AgentBuilderEventModel(
            event_id=row.id,
            session_id=row.session_id,
            event_type=row.event_type,
            status=row.status,
            input=json.loads(row.input_json or "{}"),
            output=json.loads(row.output_json or "{}"),
            error=json.loads(row.error_json or "{}"),
            created_at=row.created_at.isoformat(),
        )
