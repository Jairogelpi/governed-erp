from __future__ import annotations

import json
from dataclasses import dataclass, field

from erpguard.product.ui_recording_normalizer import NormalizedRecording
from erpguard.product.ui_selector_extractor import UISelectorExtractorService
from erpguard.db.repositories import create_ui_skill_draft
from erpguard.db.session import SessionLocal, init_db


@dataclass(frozen=True)
class UISkillDraftResult:
    draft_id: str
    session_id: str
    name: str
    description: str | None
    steps: list[dict] = field(default_factory=list)
    selector_map: dict = field(default_factory=dict)
    guard_names: list[str] = field(default_factory=list)
    status: str = "draft"


class UISkillDraftBuilder:
    _extractor = UISelectorExtractorService()

    _GUARD_TRIGGERS = {
        "formula_guard": lambda ev: (
            ev.selector and "formula" in (ev.selector or "").lower()
        ),
    }

    def build_draft(
        self,
        recording: NormalizedRecording,
        name: str,
        description: str | None = None,
    ) -> UISkillDraftResult:
        steps = self._build_steps(recording)
        selector_map = self._extractor.build_selector_map(recording.events)
        guard_names = self._infer_guards(recording)

        init_db()
        db = SessionLocal()
        try:
            row = create_ui_skill_draft(
                db,
                session_id=recording.session_id,
                name=name,
                description=description,
                steps_json=json.dumps(steps, default=str),
                selector_map_json=json.dumps(selector_map, default=str),
                guard_names_json=json.dumps(guard_names, default=str),
            )
            return UISkillDraftResult(
                draft_id=row.id,
                session_id=row.session_id,
                name=row.name,
                description=row.description,
                steps=steps,
                selector_map=selector_map,
                guard_names=guard_names,
                status=row.status,
            )
        finally:
            db.close()

    def _build_steps(self, recording: NormalizedRecording) -> list[dict]:
        steps = []
        for ev in recording.events:
            step: dict = {
                "id": f"step_{ev.event_index}",
                "type": ev.event_type,
            }
            if ev.url:
                step["url"] = ev.url
            if ev.selector:
                step["selector"] = ev.selector
            if ev.input_value is not None:
                step["value"] = ev.input_value
            if ev.element_label:
                step["label"] = ev.element_label
            steps.append(step)
        return steps

    def _infer_guards(self, recording: NormalizedRecording) -> list[str]:
        guards: list[str] = []
        for ev in recording.events:
            for guard_name, predicate in self._GUARD_TRIGGERS.items():
                if predicate(ev) and guard_name not in guards:
                    guards.append(guard_name)
        return guards
