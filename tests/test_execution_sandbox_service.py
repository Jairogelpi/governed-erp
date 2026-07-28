"""Sprint 5 — unit tests for execution sandbox services."""
from __future__ import annotations

from uuid import uuid4

import pytest

from erpguard.db.session import SessionLocal, init_db
from erpguard.product.execution_policy import ExecutionPolicyService
from erpguard.product.idempotency import IdempotencyService


@pytest.fixture(autouse=True)
def fresh_db():
    init_db()
    session = SessionLocal()
    yield session
    session.close()


# ---------------------------------------------------------------------------
# IdempotencyService
# ---------------------------------------------------------------------------

class TestIdempotencyService:
    def test_generate_key_is_deterministic(self, fresh_db):
        svc = IdempotencyService(fresh_db)
        key1 = svc.generate_key("skill_abc", {"order_ref": "SO-001"})
        key2 = svc.generate_key("skill_abc", {"order_ref": "SO-001"})
        assert key1 == key2
        assert key1.startswith("idem_")

    def test_generate_key_differs_by_inputs(self, fresh_db):
        svc = IdempotencyService(fresh_db)
        key1 = svc.generate_key("skill_abc", {"order_ref": "SO-001"})
        key2 = svc.generate_key("skill_abc", {"order_ref": "SO-002"})
        assert key1 != key2

    def test_generate_key_differs_by_skill_id(self, fresh_db):
        svc = IdempotencyService(fresh_db)
        key1 = svc.generate_key("skill_aaa", {"order_ref": "SO-001"})
        key2 = svc.generate_key("skill_bbb", {"order_ref": "SO-001"})
        assert key1 != key2

    def test_check_and_register_first_time_not_duplicate(self, fresh_db):
        svc = IdempotencyService(fresh_db)
        run_id = uuid4().hex
        key = svc.generate_key(f"skill_{run_id}", {"x": 1})
        is_dup, existing_id = svc.check_and_register(key, f"skill_{run_id}", f"exec_req_{run_id}_001")
        assert is_dup is False
        assert existing_id is None

    def test_check_and_register_second_time_is_duplicate(self, fresh_db):
        svc = IdempotencyService(fresh_db)
        run_id = uuid4().hex
        skill_id = f"skill_{run_id}"
        first_req_id = f"exec_req_{run_id}_001"
        key = svc.generate_key(skill_id, {"x": run_id})
        svc.check_and_register(key, skill_id, first_req_id)
        is_dup, existing_id = svc.check_and_register(key, skill_id, f"exec_req_{run_id}_002")
        assert is_dup is True
        assert existing_id == first_req_id


# ---------------------------------------------------------------------------
# ExecutionPolicyService
# ---------------------------------------------------------------------------

class TestExecutionPolicyService:
    def test_policy_fails_when_skill_not_found(self, fresh_db):
        svc = ExecutionPolicyService(fresh_db)
        result = svc.check("nonexistent_skill", "v1", {})
        assert result.passed is False
        codes = [v.code for v in result.violations]
        assert "skill_not_found" in codes

    def test_policy_result_never_allows_real_writes(self, fresh_db):
        svc = ExecutionPolicyService(fresh_db)
        result = svc.check("nonexistent_skill", "v1", {})
        assert result.can_execute_real_writes is False
        assert result.real_erp_writes_enabled is False

    def test_policy_to_dict_never_allows_real_writes(self, fresh_db):
        svc = ExecutionPolicyService(fresh_db)
        result = svc.check("nonexistent_skill", "v1", {})
        d = result.to_dict()
        assert d["can_execute_real_writes"] is False
        assert d["real_erp_writes_enabled"] is False
