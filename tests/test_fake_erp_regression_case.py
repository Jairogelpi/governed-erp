from __future__ import annotations

import uuid

from erpguard.db.models import UISkillVersionRecord
from erpguard.db.session import SessionLocal, init_db
from erpguard.product.fake_erp_regression_case import (
    FakeERPRegressionCaseCreateRequest,
    create_manual_fake_erp_regression_case,
    get_manual_fake_erp_regression_case,
)


def _seed_version() -> str:
    init_db()
    db = SessionLocal()
    try:
        version = UISkillVersionRecord(
            id=f"ver_{uuid.uuid4().hex[:16]}",
            skill_id=f"skill_{uuid.uuid4().hex[:8]}",
            compiled_skill_id=f"comp_{uuid.uuid4().hex[:8]}",
            name="fake-regression-case-skill",
            status="active",
            steps_json='[{"name":"Validate","operation":"fake_validate_order","target":"fake_erp"}]',
            guard_names_json='["formula_guard"]',
            runtime_type="deterministic_ui",
            llm_required=False,
            promotion_readiness_json="{}",
            is_active=True,
        )
        db.add(version)
        db.commit()
        return version.id
    finally:
        db.close()


def test_creates_manual_fake_erp_regression_case():
    version_id = _seed_version()
    init_db()
    db = SessionLocal()
    try:
        result = create_manual_fake_erp_regression_case(
            FakeERPRegressionCaseCreateRequest(
                version_id=version_id,
                dry_run_id="dryrun_demo_1",
                name="SO-VALID regression",
                inputs={"order_reference": "SO-VALID"},
                expected_outcomes={"status": "completed", "steps_executed": 1},
            ),
            db,
        )
        assert result.created is True
        assert result.case_id.startswith("fregcase_")
        fetched = get_manual_fake_erp_regression_case(case_id=result.case_id, session=db)
        assert fetched is not None
        assert fetched.inputs["order_reference"] == "SO-VALID"
    finally:
        db.close()


def test_blocks_non_fake_erp_execution_target():
    version_id = _seed_version()
    init_db()
    db = SessionLocal()
    try:
        result = create_manual_fake_erp_regression_case(
            FakeERPRegressionCaseCreateRequest(
                version_id=version_id,
                dry_run_id="dryrun_demo_1",
                name="bad target",
                execution_target="odoo",
            ),
            db,
        )
        assert result.created is False
        assert "execution_target_not_allowed:odoo" in result.blocking_reasons
    finally:
        db.close()
