from __future__ import annotations

import json

from erpguard.db.repositories import get_fake_erp_execution_evidence
from erpguard.db.session import SessionLocal, init_db
from erpguard.product.fake_erp_execution_evidence import persist_fake_erp_execution_evidence


def test_evidence_contains_executed_true_only_for_fake_erp_steps():
    init_db()
    db = SessionLocal()
    try:
        result = persist_fake_erp_execution_evidence(
            execution_id="fexec_demo_1",
            version_id="ver_demo_1",
            skill_id="skill_demo_1",
            dry_run_id="dryrun_demo_1",
            actor={"type": "user", "id": "operator_1"},
            execution_target="fake_erp",
            inputs={"order_reference": "SO-VALID"},
            steps=[
                {
                    "step_number": 1,
                    "step_name": "Validate",
                    "operation": "fake_validate_order",
                    "executed": True,
                    "execution_target": "fake_erp",
                    "real_erp_touched": False,
                    "status": "completed",
                }
            ],
            session=db,
        )
        row = get_fake_erp_execution_evidence(db, result.execution_id)
        steps = json.loads(row.steps_json)
        assert steps[0]["executed"] is True
        assert steps[0]["execution_target"] == "fake_erp"
        assert steps[0]["real_erp_touched"] is False
    finally:
        db.close()

