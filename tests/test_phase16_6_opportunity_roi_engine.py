"""Phase 16.6 -- Opportunity & ROI engine.

Builds `AnalyticalSnapshot`/`DataQualityReport`/`MarginAnalysis` rows
directly with crafted `product_drivers_json`/`customer_drivers_json`
content rather than running the full Odoo extraction pipeline (Phase 16.5
already covers extraction+quality+bridge math end to end;
this phase's rules are pure functions over already-produced driver JSON).
"""

from __future__ import annotations

import json
from decimal import Decimal
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from apps.api.main import app
from erpguard.config import settings
from erpguard.db.model_packages.decision_intelligence import (
    AnalyticalSnapshot,
    DataQualityReport,
    MarginAnalysis,
)
from erpguard.db.model_packages.opportunity import MarginOpportunity
from erpguard.db.session import SessionLocal, init_db
from erpguard.domain.opportunity.rules import cost_drift, margin_percent_erosion
from erpguard.application.opportunity.service import OpportunityEngineService, OpportunityNotFound

from test_phase14_skill_compiler import _identity


def _dump(value) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"))


def _segment(segment_id: str, net_revenue: str, cost_of_sales: str | None, gmp: str | None) -> dict:
    gross_margin = None
    if cost_of_sales is not None:
        gross_margin = str(Decimal(net_revenue) - Decimal(cost_of_sales))
    return {
        "segment_id": segment_id,
        "segment_name": f"Segment {segment_id}",
        "net_revenue": net_revenue,
        "cost_of_sales": cost_of_sales,
        "gross_margin": gross_margin,
        "gross_margin_percent": gmp,
    }


def _seed_margin_analysis(
    tenant_id: str,
    *,
    status: str,
    product_drivers: dict,
    customer_drivers: dict,
    confidence_grade: str = "A",
    cost_coverage_rate: float = 0.99,
) -> str:
    db = SessionLocal()
    try:
        snapshot_id = f"snapshot_{uuid4().hex}"
        db.add(
            AnalyticalSnapshot(
                id=snapshot_id,
                tenant_id=tenant_id,
                connection_id="conn_test",
                company_ids_json="[1]",
                period_start="2026-01-01",
                period_end="2026-01-31",
                comparison_period_start="2025-12-01",
                comparison_period_end="2025-12-31",
                source_models_json="[]",
                extraction_manifest_json="{}",
                row_counts_json="{}",
                currency="EUR",
                source_hash="hash",
                metric_definition_version="margin-truth/1.0.0",
                extraction_payload_json="{}",
                status="ready" if status == "ready" else "blocked",
                created_by="test",
            )
        )
        db.add(
            DataQualityReport(
                id=f"dq_{uuid4().hex}",
                tenant_id=tenant_id,
                snapshot_id=snapshot_id,
                checks_json="[]",
                errors_json="[]",
                warnings_json="[]",
                cost_coverage_rate=cost_coverage_rate,
                revenue_coverage_rate=0.99,
                duplicate_rate=0.0,
                refund_reconciliation_rate=1.0,
                confidence_grade=confidence_grade,
                blocking_issues_json="[]",
                content_hash="dqhash",
            )
        )
        analysis_id = f"analysis_{uuid4().hex}"
        db.add(
            MarginAnalysis(
                id=analysis_id,
                tenant_id=tenant_id,
                snapshot_id=snapshot_id,
                status=status,
                metric_definition_version="margin-truth/1.0.0",
                current_metrics_json="{}",
                comparison_metrics_json="{}",
                margin_bridge_json="{}",
                product_drivers_json=_dump(product_drivers),
                customer_drivers_json=_dump(customer_drivers),
                warnings_json="[]",
                tolerance=0.01,
                repeat_number=1,
                content_hash=f"analysishash_{uuid4().hex}",
                created_by="test",
            )
        )
        db.commit()
        return analysis_id
    finally:
        db.close()


def test_margin_percent_erosion_rule_computes_exact_impact():
    driver_pair = {
        "current": [_segment("p1", "1000", "700", "30")],
        "comparison": [_segment("p1", "1000", "500", "50")],
    }
    result = margin_percent_erosion(driver_pair, cause="test_cause", proposed_action="do X")
    assert result is not None
    assert result.affected_population == ["p1"]
    # (50 - 30) / 100 * 1000 = 200
    assert result.impact_base == Decimal("200")


def test_margin_percent_erosion_rule_skips_missing_data():
    driver_pair = {
        "current": [_segment("p1", "1000", None, None)],
        "comparison": [_segment("p1", "1000", "500", "50")],
    }
    assert margin_percent_erosion(driver_pair, cause="c", proposed_action="a") is None


def test_cost_drift_rule_computes_exact_impact():
    driver_pair = {
        "current": [_segment("p1", "1000", "600", "40")],  # cost ratio 60
        "comparison": [_segment("p1", "1000", "400", "60")],  # cost ratio 40
    }
    result = cost_drift(driver_pair)
    assert result is not None
    assert result.affected_population == ["p1"]
    # (60 - 40) / 100 * 1000 = 200
    assert result.impact_base == Decimal("200")


def test_generate_returns_empty_when_analysis_blocked(monkeypatch):
    monkeypatch.setattr(settings, "auth_secret", "skill-auth")
    init_db()
    tenant_id = f"opp-tenant-{uuid4().hex}"
    analysis_id = _seed_margin_analysis(
        tenant_id, status="blocked", product_drivers={"current": [], "comparison": []}, customer_drivers={"current": [], "comparison": []}
    )
    db = SessionLocal()
    try:
        rows = OpportunityEngineService(db).generate(tenant_id=tenant_id, margin_analysis_id=analysis_id, created_by="test")
        assert rows == []
        persisted = db.query(MarginOpportunity).filter_by(tenant_id=tenant_id, margin_analysis_id=analysis_id).all()
        assert persisted == []
    finally:
        db.close()


def test_generate_is_idempotent_and_matches_rule_math(monkeypatch):
    monkeypatch.setattr(settings, "auth_secret", "skill-auth")
    init_db()
    tenant_id = f"opp-tenant-{uuid4().hex}"
    product_drivers = {
        "current": [_segment("p1", "1000", "700", "30")],
        "comparison": [_segment("p1", "1000", "500", "50")],
    }
    customer_drivers = {"current": [], "comparison": []}
    analysis_id = _seed_margin_analysis(
        tenant_id, status="ready", product_drivers=product_drivers, customer_drivers=customer_drivers
    )
    db = SessionLocal()
    try:
        service = OpportunityEngineService(db)
        rows_1 = service.generate(tenant_id=tenant_id, margin_analysis_id=analysis_id, created_by="test")
        # This fixture's cost also grew (500 -> 700), so both the margin-percent-
        # erosion and cost-drift rules fire on the same product.
        assert {r.cause for r in rows_1} == {"product_margin_percent_erosion", "cost_drift"}
        row = next(r for r in rows_1 if r.cause == "product_margin_percent_erosion")
        assert Decimal(row.impact_base) == Decimal("200")
        assert Decimal(row.impact_conservative) == Decimal("200") * Decimal("0.6")
        assert Decimal(row.impact_optimistic) == Decimal("200") * Decimal("1.3")
        assert row.confidence_band == "high"
        assert row.risk_level == "low"

        rows_2 = service.generate(tenant_id=tenant_id, margin_analysis_id=analysis_id, created_by="test")
        assert {r.id for r in rows_2} == {r.id for r in rows_1}
        assert db.query(MarginOpportunity).filter_by(tenant_id=tenant_id, margin_analysis_id=analysis_id).count() == 2
    finally:
        db.close()


def test_generate_raises_for_unknown_analysis(monkeypatch):
    monkeypatch.setattr(settings, "auth_secret", "skill-auth")
    init_db()
    db = SessionLocal()
    try:
        with pytest.raises(OpportunityNotFound):
            OpportunityEngineService(db).generate(tenant_id="tenant-x", margin_analysis_id="missing", created_by="test")
    finally:
        db.close()


def test_margin_opportunity_rows_are_immutable(monkeypatch):
    monkeypatch.setattr(settings, "auth_secret", "skill-auth")
    init_db()
    tenant_id = f"opp-tenant-{uuid4().hex}"
    product_drivers = {
        "current": [_segment("p1", "1000", "700", "30")],
        "comparison": [_segment("p1", "1000", "500", "50")],
    }
    analysis_id = _seed_margin_analysis(
        tenant_id, status="ready", product_drivers=product_drivers, customer_drivers={"current": [], "comparison": []}
    )
    db = SessionLocal()
    try:
        OpportunityEngineService(db).generate(tenant_id=tenant_id, margin_analysis_id=analysis_id, created_by="test")
        row = (
            db.query(MarginOpportunity)
            .filter_by(tenant_id=tenant_id, margin_analysis_id=analysis_id, cause="product_margin_percent_erosion")
            .one()
        )
        row.status = "tampered"
        with pytest.raises(ValueError, match="margin_opportunity_immutable"):
            db.commit()
        db.rollback()
    finally:
        db.close()


def test_api_round_trip_generate_then_list(monkeypatch):
    monkeypatch.setattr(settings, "auth_secret", "skill-auth")
    init_db()
    tenant_id = f"opp-tenant-{uuid4().hex}"
    headers = _identity(tenant_id)
    product_drivers = {
        "current": [_segment("p1", "1000", "700", "30")],
        "comparison": [_segment("p1", "1000", "500", "50")],
    }
    analysis_id = _seed_margin_analysis(
        tenant_id, status="ready", product_drivers=product_drivers, customer_drivers={"current": [], "comparison": []}
    )
    client = TestClient(app)

    generate_resp = client.post(f"/v1/margin-analyses/{analysis_id}/opportunities", headers=headers, json={})
    assert generate_resp.status_code == 201, generate_resp.text
    body = generate_resp.json()
    assert body["blocked"] is False
    assert {o["cause"] for o in body["opportunities"]} == {"product_margin_percent_erosion", "cost_drift"}
    assert all(Decimal(o["impact_base"]) == Decimal("200") for o in body["opportunities"])

    list_resp = client.get(f"/v1/margin-analyses/{analysis_id}/opportunities", headers=headers)
    assert list_resp.status_code == 200, list_resp.text
    assert len(list_resp.json()["opportunities"]) == 2

    other_headers = _identity(f"other-tenant-{uuid4().hex}")
    other_list_resp = client.get(f"/v1/margin-analyses/{analysis_id}/opportunities", headers=other_headers)
    assert other_list_resp.status_code == 404, other_list_resp.text
