from __future__ import annotations

import json
from dataclasses import dataclass, field

from erpguard.db.repositories import get_ui_skill_version_record
from erpguard.db.session import SessionLocal, init_db


@dataclass(frozen=True)
class StepDiff:
    step_id: str
    change_type: str
    from_value: dict | None = None
    to_value: dict | None = None


@dataclass(frozen=True)
class VersionComparison:
    version_id_a: str
    version_id_b: str
    version_number_a: int
    version_number_b: int
    steps_added: list[StepDiff] = field(default_factory=list)
    steps_removed: list[StepDiff] = field(default_factory=list)
    steps_changed: list[StepDiff] = field(default_factory=list)
    guards_added: list[str] = field(default_factory=list)
    guards_removed: list[str] = field(default_factory=list)
    selectors_changed: list[dict] = field(default_factory=list)
    is_identical: bool = False
    summary: str = ""


class UISkillVersionComparator:
    def compare(self, version_id_a: str, version_id_b: str) -> VersionComparison:
        if version_id_a == version_id_b:
            raise ValueError("Cannot compare a version with itself.")

        init_db()
        db = SessionLocal()
        try:
            ver_a = get_ui_skill_version_record(db, version_id_a)
            ver_b = get_ui_skill_version_record(db, version_id_b)
            if ver_a is None:
                raise ValueError(f"Version '{version_id_a}' not found.")
            if ver_b is None:
                raise ValueError(f"Version '{version_id_b}' not found.")

            steps_a = {s.get("id", f"s{i}"): s for i, s in enumerate(json.loads(ver_a.steps_json))}
            steps_b = {s.get("id", f"s{i}"): s for i, s in enumerate(json.loads(ver_b.steps_json))}

            guards_a = set(json.loads(ver_a.guard_names_json))
            guards_b = set(json.loads(ver_b.guard_names_json))

            ids_a = set(steps_a)
            ids_b = set(steps_b)

            added = [StepDiff(sid, "added", None, steps_b[sid]) for sid in ids_b - ids_a]
            removed = [StepDiff(sid, "removed", steps_a[sid], None) for sid in ids_a - ids_b]
            changed: list[StepDiff] = []
            selectors_changed: list[dict] = []

            for sid in ids_a & ids_b:
                sa, sb = steps_a[sid], steps_b[sid]
                if sa != sb:
                    changed.append(StepDiff(sid, "changed", sa, sb))
                    sel_a = sa.get("selector")
                    sel_b = sb.get("selector")
                    if sel_a != sel_b:
                        selectors_changed.append({"step_id": sid, "from": sel_a, "to": sel_b})

            is_identical = not added and not removed and not changed
            parts = []
            if added:
                parts.append(f"{len(added)} step(s) added")
            if removed:
                parts.append(f"{len(removed)} step(s) removed")
            if changed:
                parts.append(f"{len(changed)} step(s) changed")
            if guards_b - guards_a:
                parts.append(f"{len(guards_b - guards_a)} guard(s) added")
            if guards_a - guards_b:
                parts.append(f"{len(guards_a - guards_b)} guard(s) removed")
            summary = "Versions are identical." if is_identical else "; ".join(parts) + "."

            return VersionComparison(
                version_id_a=version_id_a,
                version_id_b=version_id_b,
                version_number_a=ver_a.version_number,
                version_number_b=ver_b.version_number,
                steps_added=added,
                steps_removed=removed,
                steps_changed=changed,
                guards_added=sorted(guards_b - guards_a),
                guards_removed=sorted(guards_a - guards_b),
                selectors_changed=selectors_changed,
                is_identical=is_identical,
                summary=summary,
            )
        finally:
            db.close()
