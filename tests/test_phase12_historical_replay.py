from __future__ import annotations

import ast
from pathlib import Path
from uuid import uuid4

from fastapi.testclient import TestClient

from apps.api.main import app
from erpguard.config import settings
from erpguard.db.model_packages.identity import IdentityMembership, IdentityUser
from erpguard.db.session import SessionLocal, init_db
from erpguard.domain.events.fake_generator import build_fake_quote_to_order_ocel
from erpguard.domain.events.ocel_service import OcelEventService
from erpguard.domain.identity.auth import issue_token
from erpguard.domain.processes.registry import ProcessRegistry


ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "policies" / "processes" / "quote_to_order_v1.yaml"


def _identity(tenant_id: str, role: str = "admin") -> dict[str, str]:
    suffix = uuid4().hex
    user_id = f"replay-user-{suffix}"
    db = SessionLocal()
    db.add(IdentityUser(id=user_id, email=f"{suffix}@example.test", display_name="Replay user"))
    db.add(
        IdentityMembership(
            id=f"replay-membership-{suffix}",
            tenant_id=tenant_id,
            user_id=user_id,
            role_name=role,
            status="active",
        )
    )
    db.commit()
    db.close()
    return {"Authorization": f"Bearer {issue_token(user_id, tenant_id, 'replay-auth')}"}


def _register_process(suffix: str) -> str:
    process_key = f"replay_process_{suffix}"
    db = SessionLocal()
    try:
        base = FIXTURE.read_text(encoding="utf-8").replace("quote_to_order", process_key)
        ProcessRegistry(db).register_yaml(base)
    finally:
        db.close()
    return process_key


def _seed_cases(tenant_id: str) -> tuple[str, str]:
    """Seeds one passing and one formula-guard-blocked case. Returns their case_ids."""

    valid_key = f"so-valid-{uuid4().hex[:8]}"
    invalid_key = f"so-invalid-{uuid4().hex[:8]}"
    db = SessionLocal()
    try:
        service = OcelEventService(db)
        service.import_ocel(
            tenant_id=tenant_id,
            document=build_fake_quote_to_order_ocel(tenant_id=tenant_id, object_key=valid_key, formula_valid=True),
            source="test",
        )
        service.import_ocel(
            tenant_id=tenant_id,
            document=build_fake_quote_to_order_ocel(tenant_id=tenant_id, object_key=invalid_key, formula_valid=False),
            source="test",
        )
    finally:
        db.close()
    return valid_key, invalid_key


def _create_replay(client: TestClient, headers: dict, process_key: str) -> dict:
    response = client.post(
        f"/v1/processes/{process_key}/versions/1.0.0/replays",
        headers=headers,
        json={"object_type": "sales_order"},
    )
    assert response.status_code == 201, response.text
    return response.json()


def test_replay_produces_case_level_results_for_passing_and_blocked_cases(monkeypatch):
    monkeypatch.setattr(settings, "auth_secret", "replay-auth")
    init_db()
    tenant_id = f"replay-tenant-{uuid4().hex}"
    process_key = _register_process(uuid4().hex)
    valid_key, invalid_key = _seed_cases(tenant_id)
    headers = _identity(tenant_id)
    client = TestClient(app)

    replay = _create_replay(client, headers, process_key)
    assert replay["case_count"] == 2
    assert replay["status"] == "completed"
    assert replay["connector_simulator_version"]
    assert replay["policy_version"]

    cases_resp = client.get(f"/v1/replays/{replay['id']}/cases", headers=headers)
    assert cases_resp.status_code == 200
    cases = {row["case_id"]: row for row in cases_resp.json()}
    assert set(cases) == {valid_key, invalid_key}

    assert cases[valid_key]["status"] == "passed"
    assert cases[valid_key]["safety_violations"] == []
    assert cases[valid_key]["deterministic_trace_hash"]

    assert cases[invalid_key]["status"] == "failed"
    assert cases[invalid_key]["safety_violations"] != []
    assert cases[invalid_key]["decision_trace"][0]["decision_name"] == "formula_guard"


def test_repeatability_same_dataset_and_version_produce_identical_hashes(monkeypatch):
    monkeypatch.setattr(settings, "auth_secret", "replay-auth")
    init_db()
    tenant_id = f"replay-repeat-{uuid4().hex}"
    process_key = _register_process(uuid4().hex)
    _seed_cases(tenant_id)
    headers = _identity(tenant_id)
    client = TestClient(app)

    first = _create_replay(client, headers, process_key)
    second = _create_replay(client, headers, process_key)

    first_cases = {row["case_id"]: row["deterministic_trace_hash"] for row in client.get(f"/v1/replays/{first['id']}/cases", headers=headers).json()}
    second_cases = {row["case_id"]: row["deterministic_trace_hash"] for row in client.get(f"/v1/replays/{second['id']}/cases", headers=headers).json()}

    assert first_cases == second_cases
    assert set(first_cases.values()) == {v for v in second_cases.values()}


def test_needs_clarification_when_recorded_state_cannot_build_a_sales_order(monkeypatch):
    monkeypatch.setattr(settings, "auth_secret", "replay-auth")
    init_db()
    tenant_id = f"replay-ambiguous-{uuid4().hex}"
    process_key = _register_process(uuid4().hex)
    db = SessionLocal()
    try:
        OcelEventService(db).import_ocel(
            tenant_id=tenant_id,
            document={
                "ocel:objects": {"so-ambiguous": {"ocel:type": "sale_order", "ocel:ovmap": {}}},
                "ocel:events": {
                    "e-1": {
                        "ocel:activity": "sales.quote.created",
                        "ocel:timestamp": "2026-01-01T00:00:00Z",
                        "ocel:omap": ["so-ambiguous"],
                        "ocel:vmap": {},
                    },
                    "e-2": {
                        "ocel:activity": "sales.quote.reviewed",
                        "ocel:timestamp": "2026-01-01T00:01:00Z",
                        "ocel:omap": ["so-ambiguous"],
                        "ocel:vmap": {},
                    },
                },
            },
            source="test",
        )
    finally:
        db.close()
    headers = _identity(tenant_id)
    client = TestClient(app)

    replay = _create_replay(client, headers, process_key)
    cases = client.get(f"/v1/replays/{replay['id']}/cases", headers=headers).json()
    assert len(cases) == 1
    assert cases[0]["status"] == "needs_clarification"
    assert cases[0]["deterministic_trace_hash"]


def test_freeze_makes_a_replay_immutable(monkeypatch):
    monkeypatch.setattr(settings, "auth_secret", "replay-auth")
    init_db()
    tenant_id = f"replay-freeze-{uuid4().hex}"
    process_key = _register_process(uuid4().hex)
    _seed_cases(tenant_id)
    headers = _identity(tenant_id, role="admin")
    client = TestClient(app)

    replay = _create_replay(client, headers, process_key)
    frozen = client.post(f"/v1/replays/{replay['id']}/freeze", headers=headers)
    assert frozen.status_code == 200
    assert frozen.json()["status"] == "frozen"
    assert frozen.json()["frozen_at"]

    second_attempt = client.post(f"/v1/replays/{replay['id']}/freeze", headers=headers)
    assert second_attempt.status_code == 400


def test_comparison_endpoint_reports_matched_cases_and_hash_agreement(monkeypatch):
    monkeypatch.setattr(settings, "auth_secret", "replay-auth")
    init_db()
    tenant_id = f"replay-compare-{uuid4().hex}"
    process_key = _register_process(uuid4().hex)
    _seed_cases(tenant_id)
    headers = _identity(tenant_id)
    client = TestClient(app)

    baseline = _create_replay(client, headers, process_key)
    candidate = _create_replay(client, headers, process_key)

    comparison = client.get(
        f"/v1/replays/{candidate['id']}/comparison",
        headers=headers,
        params={"baseline_replay_id": baseline["id"]},
    )
    assert comparison.status_code == 200
    body = comparison.json()
    assert body["compared_case_count"] == 2
    assert body["matched_case_count"] == 2
    assert body["only_in_baseline_case_ids"] == []
    assert body["only_in_candidate_case_ids"] == []
    assert all(case["hash_matches"] for case in body["cases"])


def test_replay_api_is_tenant_scoped(monkeypatch):
    monkeypatch.setattr(settings, "auth_secret", "replay-auth")
    init_db()
    process_key = _register_process(uuid4().hex)
    tenant_a = f"replay-tenant-a-{uuid4().hex}"
    tenant_b = f"replay-tenant-b-{uuid4().hex}"
    _seed_cases(tenant_a)
    headers_a = _identity(tenant_a)
    headers_b = _identity(tenant_b)
    client = TestClient(app)

    replay = _create_replay(client, headers_a, process_key)
    assert client.get(f"/v1/replays/{replay['id']}", headers=headers_b).status_code == 404
    assert client.get(f"/v1/replays/{replay['id']}/cases", headers=headers_b).status_code == 404


def test_no_llm_or_agent_runtime_import_in_replay_engine():
    module_dir = ROOT / "erpguard" / "domain" / "replays"
    forbidden_substrings = ("llm", "agent")
    for path in module_dir.glob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                names = [alias.name for alias in node.names]
            elif isinstance(node, ast.ImportFrom) and node.module:
                names = [node.module]
            else:
                continue
            for name in names:
                lowered = name.lower()
                assert not any(token in lowered for token in forbidden_substrings), (
                    f"{path} imports '{name}', which looks like an LLM/agent-runtime module; "
                    "historical replay must never invoke one (spec 15.7)."
                )
