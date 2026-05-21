from __future__ import annotations

import json

from erpguard.core.errors import ObjectNotFoundError
from erpguard.db.repositories import (
    create_r2_evidence_review,
    get_r2_evidence_review_for_run,
    get_r2_write_pilot_run,
    list_r2_write_pilot_evidence_for_run,
)


class R2EvidenceReviewService:
    def __init__(self, session) -> None:
        self.session = session

    def get_or_create(self, run_id: str) -> dict:
        existing = get_r2_evidence_review_for_run(self.session, run_id)
        if existing:
            return self._to_dict(existing)

        run_row = get_r2_write_pilot_run(self.session, run_id)
        if run_row is None:
            raise ObjectNotFoundError(f"R2 write pilot run '{run_id}' not found.")

        evidence_rows = list_r2_write_pilot_evidence_for_run(self.session, run_id)

        pre_fields = _extract_field_values(
            json.loads(run_row.pre_snapshot_json).get("field_values", {})
        )
        post_fields = _extract_field_values(
            json.loads(run_row.post_snapshot_json).get("field_values", {})
        )

        delta, changed, unchanged, drift_items = _compute_delta(pre_fields, post_fields)

        rollback = {}
        if evidence_rows:
            rollback = json.loads(evidence_rows[0].rollback_instructions_json)

        row = create_r2_evidence_review(
            self.session,
            run_id=run_id,
            skill_id=run_row.skill_id,
            delta_json=json.dumps(delta),
            fields_changed=changed,
            fields_unchanged=unchanged,
            drift_detected=len(drift_items) > 0,
            drift_details_json=json.dumps(drift_items),
            status="completed",
        )
        return self._to_dict(row, run_row=run_row, rollback=rollback)

    @staticmethod
    def _to_dict(row, run_row=None, rollback: dict | None = None) -> dict:
        return {
            "review_id": row.id,
            "run_id": row.run_id,
            "skill_id": row.skill_id,
            "delta": json.loads(row.delta_json),
            "fields_changed": row.fields_changed,
            "fields_unchanged": row.fields_unchanged,
            "drift_detected": row.drift_detected,
            "drift_details": json.loads(row.drift_details_json),
            "status": row.status,
            "rollback_instructions": rollback or {},
            "safety_invariants": {
                "can_execute_real_writes": False,
                "allow_generic_real_odoo_writes": False,
                "allow_r3_r4_real_writes": False,
            },
            "created_at": row.created_at.isoformat(),
        }


def _extract_field_values(field_map: dict) -> dict:
    if isinstance(field_map, dict):
        return {k: str(v) for k, v in field_map.items()}
    return {}


def _compute_delta(pre: dict, post: dict) -> tuple[dict, int, int, list]:
    all_keys = set(pre) | set(post)
    delta: dict = {}
    drift_items: list = []
    changed = 0
    unchanged = 0

    for key in sorted(all_keys):
        pre_val = pre.get(key, "<missing>")
        post_val = post.get(key, "<missing>")
        if pre_val != post_val:
            delta[key] = {"before": pre_val, "after": post_val}
            changed += 1
        else:
            unchanged += 1

    if post and pre and post == pre and changed == 0:
        pass
    elif post and pre and changed == 0 and not pre:
        pass

    for key, vals in delta.items():
        if vals["after"] == "<missing>" and vals["before"] != "<missing>":
            drift_items.append({"field": key, "issue": "field disappeared after write"})
        elif vals["before"] == "<missing>" and vals["after"] != "<missing>":
            drift_items.append({"field": key, "issue": "unexpected field appeared after write"})

    return delta, changed, unchanged, drift_items
