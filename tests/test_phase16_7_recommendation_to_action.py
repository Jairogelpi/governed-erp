"""Spec 92 Workstream A -- MarginOpportunity -> GovernedRecommendation -> GovernedActionDraft.

Builds a `MarginOpportunity` the same direct-row way
`test_phase16_6_opportunity_roi_engine.py` does (crafted driver JSON, no
full Odoo extraction pipeline), then drives `RecommendationService`
through the public API.
"""

from __future__ import annotations

from uuid import uuid4

import pytest
from cryptography.fernet import Fernet
from fastapi.testclient import TestClient

from apps.api.main import app
from erpguard.config import settings
from erpguard.db.model_packages.opportunity import MarginOpportunity
from erpguard.db.session import SessionLocal, init_db

from test_phase14_skill_compiler import _identity
from test_phase16_6_opportunity_roi_engine import _dump, _seed_margin_analysis, _segment


def _setup(monkeypatch) -> tuple[TestClient, dict, str]:
    monkeypatch.setattr(settings, "auth_secret", "skill-auth")
    monkeypatch.setattr(settings, "local_secret_key", Fernet.generate_key().decode())
    init_db()
    tenant_id = f"rec-tenant-{uuid4().hex}"
    headers = _identity(tenant_id)
    return TestClient(app), headers, tenant_id


def _seed_opportunity(tenant_id: str, *, blocked: bool = False) -> str:
    product_drivers = {
        "current": [_segment("p1", "1000", "700", "30")],
        "comparison": [_segment("p1", "1000", "500", "50")],
    }
    analysis_id = _seed_margin_analysis(
        tenant_id,
        status="blocked" if blocked else "ready",
        product_drivers=product_drivers,
        customer_drivers={"current": [], "comparison": []},
    )
    if blocked:
        opportunity_id = f"opp_{uuid4().hex}"
        db = SessionLocal()
        try:
            db.add(
                MarginOpportunity(
                    id=opportunity_id,
                    tenant_id=tenant_id,
                    margin_analysis_id=analysis_id,
                    snapshot_id="snapshot_x",
                    cause="product_margin_percent_erosion",
                    affected_population_json=_dump(["p1"]),
                    evidence_json=_dump([]),
                    impact_conservative="120",
                    impact_base="200",
                    impact_optimistic="260",
                    confidence_band="high",
                    risk_level="low",
                    proposed_action="review pricing",
                    created_by="test",
                    content_hash=f"hash_{uuid4().hex}",
                )
            )
            db.commit()
        finally:
            db.close()
        return opportunity_id

    from erpguard.application.opportunity.service import OpportunityEngineService

    db = SessionLocal()
    try:
        rows = OpportunityEngineService(db).generate(tenant_id=tenant_id, margin_analysis_id=analysis_id, created_by="test")
        return rows[0].id
    finally:
        db.close()


def test_blocked_analysis_cannot_produce_recommendation(monkeypatch):
    client, headers, tenant_id = _setup(monkeypatch)
    opportunity_id = _seed_opportunity(tenant_id, blocked=True)

    resp = client.post(
        f"/v1/opportunities/{opportunity_id}/recommendations",
        headers=headers,
        json={
            "recommendation_type": "product_price_review",
            "title": "Review pricing",
            "selected_action_template": "product_price_review_v1",
        },
    )
    assert resp.status_code == 400, resp.text
    assert "blocked" in resp.json()["detail"]


def test_opportunity_from_another_tenant_is_invisible(monkeypatch):
    client, headers, tenant_id = _setup(monkeypatch)
    opportunity_id = _seed_opportunity(tenant_id)

    other_headers = _identity(f"other-tenant-{uuid4().hex}")
    resp = client.post(
        f"/v1/opportunities/{opportunity_id}/recommendations",
        headers=other_headers,
        json={
            "recommendation_type": "product_price_review",
            "title": "Review pricing",
            "selected_action_template": "product_price_review_v1",
        },
    )
    assert resp.status_code == 400, resp.text
    assert "not_found" in resp.json()["detail"]


def test_recommendation_hash_is_reproducible(monkeypatch):
    client, headers, tenant_id = _setup(monkeypatch)
    opportunity_id = _seed_opportunity(tenant_id)

    from erpguard.application.recommendations.service import RecommendationService

    db = SessionLocal()
    try:
        service = RecommendationService(db)
        row_1 = service.create(
            tenant_id=tenant_id, opportunity_id=opportunity_id, recommendation_type="product_price_review",
            title="A", selected_action_template="product_price_review_v1", created_by="tester",
        )
        row_2 = service.create(
            tenant_id=tenant_id, opportunity_id=opportunity_id, recommendation_type="product_price_review",
            title="B", selected_action_template="product_price_review_v1", created_by="tester",
        )
        assert row_1.content_hash == row_2.content_hash
    finally:
        db.close()


def test_submit_freezes_content_and_creator_cannot_approve(monkeypatch):
    client, headers, tenant_id = _setup(monkeypatch)
    opportunity_id = _seed_opportunity(tenant_id)

    create_resp = client.post(
        f"/v1/opportunities/{opportunity_id}/recommendations",
        headers=headers,
        json={
            "recommendation_type": "product_price_review",
            "title": "Review pricing",
            "selected_action_template": "product_price_review_v1",
        },
    )
    assert create_resp.status_code == 201, create_resp.text
    recommendation = create_resp.json()

    submit_resp = client.post(f"/v1/recommendations/{recommendation['id']}/submit", headers=headers)
    assert submit_resp.status_code == 200, submit_resp.text

    db = SessionLocal()
    try:
        from erpguard.db.model_packages.recommendations import GovernedRecommendation

        row = db.query(GovernedRecommendation).filter_by(tenant_id=tenant_id, id=recommendation["id"]).one()
        row.title = "tampered"
        with pytest.raises(ValueError, match="governed_recommendation_title_immutable"):
            db.commit()
        db.rollback()
    finally:
        db.close()

    approval_resp = client.post("/v1/approvals", headers=headers, json={"scope": recommendation["approval_scope"]})
    assert approval_resp.status_code == 201, approval_resp.text
    approval_id = approval_resp.json()["id"]

    approve_resp = client.post(
        f"/v1/recommendations/{recommendation['id']}/approve", headers=headers, json={"approval_id": approval_id}
    )
    assert approve_resp.status_code == 400, approve_resp.text
    assert "creator_cannot_approve" in approve_resp.json()["detail"]


def test_expired_approval_blocks_conversion(monkeypatch):
    client, headers, tenant_id = _setup(monkeypatch)
    monkeypatch.setattr(settings, "recommendation_approval_max_age_seconds", 0)
    opportunity_id = _seed_opportunity(tenant_id)

    create_resp = client.post(
        f"/v1/opportunities/{opportunity_id}/recommendations",
        headers=headers,
        json={
            "recommendation_type": "product_price_review",
            "title": "Review pricing",
            "selected_action_template": "product_price_review_v1",
        },
    )
    recommendation = create_resp.json()
    assert client.post(f"/v1/recommendations/{recommendation['id']}/submit", headers=headers).status_code == 200

    other_headers = _identity(f"approver-tenant-{uuid4().hex}")
    # Approver must be in the same tenant to see the recommendation; reuse tenant_id, different user.
    approver_headers = _identity(tenant_id)
    approval_resp = client.post(
        "/v1/approvals", headers=approver_headers, json={"scope": recommendation["approval_scope"]}
    )
    approval_id = approval_resp.json()["id"]

    import time

    time.sleep(1.1)
    approve_resp = client.post(
        f"/v1/recommendations/{recommendation['id']}/approve",
        headers=approver_headers,
        json={"approval_id": approval_id},
    )
    assert approve_resp.status_code == 400, approve_resp.text
    assert "approval_expired" in approve_resp.json()["detail"]


def test_unsupported_action_template_remains_review_only(monkeypatch):
    client, headers, tenant_id = _setup(monkeypatch)
    opportunity_id = _seed_opportunity(tenant_id)

    create_resp = client.post(
        f"/v1/opportunities/{opportunity_id}/recommendations",
        headers=headers,
        json={
            "recommendation_type": "cost_drift_review",
            "title": "Cost drift",
            "selected_action_template": "cost_drift_review_v1",
        },
    )
    recommendation = create_resp.json()
    assert client.post(f"/v1/recommendations/{recommendation['id']}/submit", headers=headers).status_code == 200

    approver_headers = _identity(tenant_id)
    approval_id = client.post(
        "/v1/approvals", headers=approver_headers, json={"scope": recommendation["approval_scope"]}
    ).json()["id"]
    approve_resp = client.post(
        f"/v1/recommendations/{recommendation['id']}/approve",
        headers=approver_headers,
        json={"approval_id": approval_id},
    )
    assert approve_resp.status_code == 200, approve_resp.text

    draft_resp = client.post(
        f"/v1/recommendations/{recommendation['id']}/action-drafts",
        headers=headers,
        json={"process_key": "irrelevant_process"},
    )
    assert draft_resp.status_code == 201, draft_resp.text
    assert draft_resp.json()["execution_classification"] == "review_only"
    assert draft_resp.json()["capability"] == ""


def test_changed_source_hash_scenario_is_independent_recommendation(monkeypatch):
    """A recommendation's content_hash depends on the opportunity's
    content_hash at creation time; a differently-derived opportunity (even
    same cause/population) produces a different recommendation hash."""

    client, headers, tenant_id = _setup(monkeypatch)
    opportunity_id_1 = _seed_opportunity(tenant_id)
    opportunity_id_2 = _seed_opportunity(tenant_id)
    assert opportunity_id_1 != opportunity_id_2

    from erpguard.application.recommendations.service import RecommendationService

    db = SessionLocal()
    try:
        service = RecommendationService(db)
        row_1 = service.create(
            tenant_id=tenant_id, opportunity_id=opportunity_id_1, recommendation_type="product_price_review",
            title="A", selected_action_template="product_price_review_v1", created_by="tester",
        )
        row_2 = service.create(
            tenant_id=tenant_id, opportunity_id=opportunity_id_2, recommendation_type="product_price_review",
            title="A", selected_action_template="product_price_review_v1", created_by="tester",
        )
        assert row_1.content_hash != row_2.content_hash
        assert row_1.source_content_hash != row_2.source_content_hash
    finally:
        db.close()
