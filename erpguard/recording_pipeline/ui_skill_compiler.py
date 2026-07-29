from __future__ import annotations

import json
from dataclasses import dataclass, field

from erpguard.db.repositories import create_ui_compiled_skill, get_ui_skill_draft
from erpguard.db.session import SessionLocal, init_db


@dataclass(frozen=True)
class UICompiledSkillResult:
    compiled_skill_id: str
    draft_id: str
    session_id: str
    name: str
    runtime_type: str
    steps: list[dict] = field(default_factory=list)
    guard_names: list[str] = field(default_factory=list)
    llm_required: bool = False
    status: str = "compiled"


class UISkillCompilerService:
    def compile(self, draft_id: str) -> UICompiledSkillResult:
        init_db()
        db = SessionLocal()
        try:
            draft = get_ui_skill_draft(db, draft_id)
            if draft is None:
                raise ValueError(f"UI skill draft '{draft_id}' not found.")

            steps = json.loads(draft.steps_json)
            guard_names = json.loads(draft.guard_names_json)
            compiled_steps = self._compile_steps(steps)

            row = create_ui_compiled_skill(
                db,
                draft_id=draft.id,
                session_id=draft.session_id,
                name=draft.name,
                steps_json=json.dumps(compiled_steps, default=str),
                guard_names_json=draft.guard_names_json,
            )
            return UICompiledSkillResult(
                compiled_skill_id=row.id,
                draft_id=row.draft_id,
                session_id=row.session_id,
                name=row.name,
                runtime_type=row.runtime_type,
                steps=compiled_steps,
                guard_names=guard_names,
                llm_required=False,
                status=row.status,
            )
        finally:
            db.close()

    def _compile_steps(self, steps: list[dict]) -> list[dict]:
        compiled = []
        for step in steps:
            cs = dict(step)
            cs["compiled"] = True
            cs["llm_required"] = False
            cs["deterministic"] = True
            compiled.append(cs)
        return compiled
