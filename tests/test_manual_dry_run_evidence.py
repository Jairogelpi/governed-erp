from __future__ import annotations

import json

from erpguard.db.repositories import get_manual_dry_run_evidence_for_run
from erpguard.product.manual_dry_run_evidence import persist_manual_dry_run_evidence
from erpguard.db.session import SessionLocal, init_db


def test_evidence_contains_would_execute_but_executed_false():
    init_db()
    db = SessionLocal()
    try:
        persist_manual_dry_run_evidence(
            run_id="as_run_manual_evidence_1",
            version_id="ver_manual_evidence_1",
            skill_id="skill_manual_evidence_1",
            actor={"type": "user", "id": "operator_1", "display_name": "Operator"},
            mode="dry_run",
            inputs={"order_reference": "SO-VALID"},
            preview_reference_id="asrpe_123",
            source_plan_id="aplan_123",
            source_step_number=4,
            gate_result={"passed": True},
            steps_json='[{"name":"Open sales order"}]',
            session=db,
        )
        row = get_manual_dry_run_evidence_for_run(db, "as_run_manual_evidence_1")
        would_steps = json.loads(row.would_execute_steps_json)
        sim_steps = json.loads(row.simulated_steps_json)
        assert len(would_steps) == 1
        assert would_steps[0]["would_execute"] is True
        assert would_steps[0]["executed"] is False
        assert sim_steps[0]["executed"] is False
    finally:
        db.close()
