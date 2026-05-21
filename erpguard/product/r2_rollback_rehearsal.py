from __future__ import annotations

import json

from erpguard.core.errors import ObjectNotFoundError
from erpguard.db.repositories import (
    create_r2_rollback_rehearsal,
    get_r2_rollback_rehearsal_for_run,
    get_r2_write_pilot_run,
    list_r2_write_pilot_evidence_for_run,
)

_REQUIRED_INSTRUCTION_KEYS = frozenset({"action", "model", "record_id", "restore_vals", "odoo_call"})


class R2RollbackRehearsalService:
    def __init__(self, session) -> None:
        self.session = session

    def rehearse(self, run_id: str) -> dict:
        existing = get_r2_rollback_rehearsal_for_run(self.session, run_id)
        if existing:
            return self._to_dict(existing)

        run_row = get_r2_write_pilot_run(self.session, run_id)
        if run_row is None:
            raise ObjectNotFoundError(f"R2 write pilot run '{run_id}' not found.")

        evidence_rows = list_r2_write_pilot_evidence_for_run(self.session, run_id)
        if not evidence_rows:
            return self._store_and_dict(run_id, run_row.skill_id, valid=False, missing=["no evidence stored"], steps=[], notes="No evidence found — execute the pilot first.")

        rollback = json.loads(evidence_rows[0].rollback_instructions_json)

        missing = sorted(_REQUIRED_INSTRUCTION_KEYS - set(rollback.keys()))
        valid = len(missing) == 0

        steps = []
        if valid:
            steps = [
                {"step": 1, "action": "verify", "description": f"Confirm record {rollback.get('record_id')} exists in {rollback.get('model')}"},
                {"step": 2, "action": "inspect", "description": f"Inspect current field values: {list(rollback.get('restore_vals', {}).keys())}"},
                {"step": 3, "action": "dry_run", "description": "DRY-RUN ONLY: validate the Odoo call syntax without executing"},
                {"step": 4, "action": "odoo_call_preview", "description": rollback.get("odoo_call", ""), "execute": False},
                {"step": 5, "action": "confirm", "description": "Human operator must confirm before any real rollback execution"},
            ]

        notes = (
            "Rehearsal passed. Rollback instructions are complete and validated (dry-run only)."
            if valid else
            f"Rehearsal failed: missing fields {missing}. Complete evidence capture before rehearsing rollback."
        )

        return self._store_and_dict(run_id, run_row.skill_id, valid=valid, missing=missing, steps=steps, notes=notes)

    def _store_and_dict(self, run_id: str, skill_id: str, *, valid: bool, missing: list, steps: list, notes: str) -> dict:
        row = create_r2_rollback_rehearsal(
            self.session,
            run_id=run_id,
            skill_id=skill_id,
            instructions_valid=valid,
            missing_fields_json=json.dumps(missing),
            dry_run_steps_json=json.dumps(steps),
            rehearsal_passed=valid,
            notes=notes,
        )
        return self._to_dict(row)

    @staticmethod
    def _to_dict(row) -> dict:
        return {
            "rehearsal_id": row.id,
            "run_id": row.run_id,
            "skill_id": row.skill_id,
            "instructions_valid": row.instructions_valid,
            "missing_fields": json.loads(row.missing_fields_json),
            "dry_run_steps": json.loads(row.dry_run_steps_json),
            "rehearsal_passed": row.rehearsal_passed,
            "notes": row.notes,
            "real_rollback_executed": False,
            "safety_invariants": {
                "can_execute_real_writes": False,
                "allow_generic_real_odoo_writes": False,
                "allow_r3_r4_real_writes": False,
            },
            "created_at": row.created_at.isoformat(),
        }
