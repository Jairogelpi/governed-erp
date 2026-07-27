from __future__ import annotations

from pathlib import Path
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from apps.api.main import app
from erpguard.config import settings
from erpguard.db.model_packages.identity import IdentityMembership, IdentityUser
from erpguard.db.session import SessionLocal, init_db
from erpguard.domain.identity.auth import issue_token
from erpguard.domain.processes.registry import ProcessDefinitionConflict, ProcessRegistry
from erpguard.domain.processes.validation import ProcessValidationError, load_process_yaml


ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "policies" / "processes" / "quote_to_order_v1.yaml"


def test_quote_to_order_fixture_validates():
    definition = load_process_yaml(FIXTURE.read_text(encoding="utf-8"))
    assert definition.process_key == "quote_to_order"
    assert definition.version == "1.0.0"
    assert "sales_order_created" in {event.name for event in definition.events}
    assert definition.metrics


def test_invalid_process_definition_is_blocked():
    with pytest.raises(ProcessValidationError):
        load_process_yaml("process_key: quote_to_order\nversion: 1.0.0\nobjects: []\nevents: []")


def test_registry_stores_immutable_version_and_computes_diff():
    init_db()
    db = SessionLocal()
    process_key = f"quote_to_order_{uuid4().hex}"
    base = FIXTURE.read_text(encoding="utf-8").replace("quote_to_order", process_key)
    try:
        registry = ProcessRegistry(db)
        first = registry.register_yaml(base)
        same = registry.register_yaml(base)
        assert first.id == same.id
        changed = base.replace("Quote-to-Order baseline", "Quote-to-Order changed")
        changed = changed.replace("version: 1.0.0", "version: 1.1.0")
        registry.register_yaml(changed)
        diff = registry.diff(process_key, "1.0.0", "1.1.0")
        assert diff["changed"]
        with pytest.raises(ProcessDefinitionConflict):
            registry.register_yaml(base.replace("Quote-to-Order baseline", "Conflicting baseline"))
    finally:
        db.close()


def test_process_registry_api_registers_and_diffs_with_identity(monkeypatch):
    init_db()
    monkeypatch.setattr(settings, "auth_secret", "phase9-auth")
    tenant = f"phase9-api-{uuid4().hex}"
    user_id = f"phase9-admin-{uuid4().hex}"
    db = SessionLocal()
    db.add(IdentityUser(id=user_id, email=f"{user_id}@example.test", display_name="Phase 9"))
    db.add(IdentityMembership(
        id=f"phase9-membership-{uuid4().hex}", tenant_id=tenant, user_id=user_id,
        role_name="admin", status="active",
    ))
    db.commit()
    db.close()
    headers = {"Authorization": f"Bearer {issue_token(user_id, tenant, 'phase9-auth')}"}
    process_key = f"quote_to_order_api_{uuid4().hex}"
    base = FIXTURE.read_text(encoding="utf-8").replace("quote_to_order", process_key)
    client = TestClient(app)
    created = client.post("/v1/processes", headers=headers, json={"yaml": base})
    assert created.status_code == 201
    fetched = client.get(f"/v1/processes/{process_key}/versions/1.0.0", headers=headers)
    assert fetched.status_code == 200
    assert fetched.json()["process_key"] == process_key
    changed = base.replace("Quote-to-Order baseline", "Quote-to-Order API changed").replace(
        "version: 1.0.0", "version: 1.1.0"
    )
    assert client.post("/v1/processes", headers=headers, json={"yaml": changed}).status_code == 201
    diff = client.get(
        f"/v1/processes/{process_key}/diff?from_version=1.0.0&to_version=1.1.0",
        headers=headers,
    )
    assert diff.status_code == 200
    assert diff.json()["changed"] is True
