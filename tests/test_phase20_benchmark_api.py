"""Spec 93 -- POST /v1/benchmarks/runs, GET .../runs/{id}, GET .../report
through the public API against the real committed dataset
(docs/benchmark/datasets/quote_to_order_v1_seed92)."""

from __future__ import annotations

from uuid import uuid4

from cryptography.fernet import Fernet
from fastapi.testclient import TestClient

from apps.api.main import app
from erpguard.config import settings
from erpguard.db.session import init_db

from test_phase14_skill_compiler import _identity

_DATASET_VERSION = "quote_to_order_v1_seed92"


def _setup(monkeypatch) -> tuple[TestClient, dict, str]:
    monkeypatch.setattr(settings, "auth_secret", "skill-auth")
    monkeypatch.setattr(settings, "local_secret_key", Fernet.generate_key().decode())
    init_db()
    tenant_id = f"benchmark-api-tenant-{uuid4().hex}"
    headers = _identity(tenant_id)
    return TestClient(app), headers, tenant_id


def test_create_run_report_and_get(monkeypatch):
    client, headers, tenant_id = _setup(monkeypatch)

    create_resp = client.post(
        "/v1/benchmarks/runs", headers=headers,
        json={"dataset_version": _DATASET_VERSION, "configurations": ["fixed_workflow", "erpguard_candidate"], "repeats": 1},
    )
    assert create_resp.status_code == 201, create_resp.text
    run = create_resp.json()
    assert run["status"] == "completed"
    assert run["dataset_version"] == _DATASET_VERSION
    assert set(run["configurations"]) == {"fixed_workflow", "erpguard_candidate"}

    get_resp = client.get(f"/v1/benchmarks/runs/{run['id']}", headers=headers)
    assert get_resp.status_code == 200, get_resp.text
    assert get_resp.json()["id"] == run["id"]

    report_resp = client.get(f"/v1/benchmarks/runs/{run['id']}/report", headers=headers)
    assert report_resp.status_code == 200, report_resp.text
    report = report_resp.json()
    assert report["dataset_version"] == _DATASET_VERSION
    assert set(report["configurations"]) == {"fixed_workflow", "erpguard_candidate"}
    assert report["configurations"]["fixed_workflow"]["case_count"] == 120


def test_unknown_dataset_version_rejected(monkeypatch):
    client, headers, tenant_id = _setup(monkeypatch)
    resp = client.post(
        "/v1/benchmarks/runs", headers=headers,
        json={"dataset_version": "does_not_exist", "configurations": ["fixed_workflow"], "repeats": 1},
    )
    assert resp.status_code == 400, resp.text
    assert "dataset_version_not_found" in resp.json()["detail"]


def test_unknown_configuration_rejected(monkeypatch):
    client, headers, tenant_id = _setup(monkeypatch)
    resp = client.post(
        "/v1/benchmarks/runs", headers=headers,
        json={"dataset_version": _DATASET_VERSION, "configurations": ["not_a_real_config"], "repeats": 1},
    )
    assert resp.status_code == 400, resp.text
    assert "unknown_benchmark_configurations" in resp.json()["detail"]


def test_another_tenant_cannot_read_run(monkeypatch):
    client, headers, tenant_id = _setup(monkeypatch)
    run = client.post(
        "/v1/benchmarks/runs", headers=headers,
        json={"dataset_version": _DATASET_VERSION, "configurations": ["fixed_workflow"], "repeats": 1},
    ).json()

    other_headers = _identity(f"other-tenant-{uuid4().hex}")
    resp = client.get(f"/v1/benchmarks/runs/{run['id']}", headers=other_headers)
    assert resp.status_code == 404
