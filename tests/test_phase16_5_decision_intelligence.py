from __future__ import annotations

import json
from decimal import Decimal
from typing import Any
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from apps.api.main import app
from erpguard.application.connectors.service import ConnectorApplicationService
from erpguard.application.decision_intelligence.extraction_service import SOURCE_FIELDS
from erpguard.config import settings
from erpguard.connectors.sdk.models import ConnectorContext
from erpguard.db.model_packages.decision_intelligence import AnalyticalSnapshot
from erpguard.db.model_packages.identity import IdentityMembership, IdentityUser
from erpguard.db.session import SessionLocal, init_db
from erpguard.domain.identity.auth import issue_token


class AnalyticalReadTransport:
    def __init__(
        self,
        *,
        missing_costs: bool = False,
        unavailable_models: set[str] | None = None,
        missing_fields: dict[str, set[str]] | None = None,
    ):
        self.calls: list[tuple[str, str]] = []
        self.unavailable_models = unavailable_models or set()
        self.missing_fields = missing_fields or {}
        standard_price: float | None = None if missing_costs else 60.0
        self.rows: dict[str, list[dict[str, Any]]] = {
            "account.move": [
                _move(1, "INV/BASE", "out_invoice", "2026-01-15", 10),
                _move(2, "RINV/BASE", "out_refund", "2026-01-20", 10, reversed_id=1),
                _move(3, "INV/CURRENT-A", "out_invoice", "2026-02-15", 10),
                _move(4, "INV/CURRENT-B", "out_invoice", "2026-02-18", 20),
                _move(5, "RINV/CURRENT", "out_refund", "2026-02-22", 20, reversed_id=4),
            ],
            "account.move.line": [
                _line(101, 1, 100, 10, 100, 10, 900),
                _line(102, 2, 100, 1, 100, 10, 90),
                _line(103, 3, 100, 12, 110, 10, 1188),
                _line(104, 4, 200, 10, 80, 0, 800),
                _line(105, 5, 200, 2, 80, 0, 160),
            ],
            "sale.order": [],
            "sale.order.line": [],
            "product.product": [
                {
                    "id": 100,
                    "display_name": "Aroma A",
                    "default_code": "A",
                    "standard_price": standard_price,
                },
                {
                    "id": 200,
                    "display_name": "Aroma B",
                    "default_code": "B",
                    "standard_price": None if missing_costs else 50.0,
                },
            ],
            "res.partner": [
                {"id": 10, "display_name": "Cliente Base", "name": "Cliente Base"},
                {"id": 20, "display_name": "Cliente Nuevo", "name": "Cliente Nuevo"},
            ],
            "res.company": [
                {
                    "id": 1,
                    "display_name": "Esenssi",
                    "name": "Esenssi",
                    "currency_id": [1, "EUR"],
                }
            ],
            "res.currency": [{"id": 1, "name": "EUR", "symbol": "€"}],
            "stock.valuation.layer": (
                []
                if missing_costs
                else [
                    _valuation(1, 100, 60, "2026-01-01 00:00:00"),
                    _valuation(2, 100, 70, "2026-02-01 00:00:00"),
                    _valuation(3, 200, 50, "2026-02-01 00:00:00"),
                    _valuation(
                        4,
                        100,
                        999,
                        "2026-01-10 00:00:00",
                        company_id=2,
                    ),
                ]
            ),
        }

    def _check(self, model: str) -> None:
        if model in self.unavailable_models:
            raise RuntimeError(f"{model} unavailable")

    def version(self) -> dict[str, Any]:
        self.calls.append(("common", "version"))
        return {"server_version": "19.0-test"}

    def authenticate(self) -> int:
        self.calls.append(("common", "authenticate"))
        return 2

    def fields_get(
        self,
        model: str,
        attributes: list[str] | None = None,
    ) -> dict[str, dict[str, str]]:
        self._check(model)
        self.calls.append((model, "fields_get"))
        excluded = self.missing_fields.get(model, set())
        return {
            field: {"type": "test", "string": field}
            for field in SOURCE_FIELDS[model]
            if field not in excluded
        }

    def search_count(self, model: str, domain: list) -> int:
        self._check(model)
        self.calls.append((model, "search_count"))
        return len(self.rows[model])

    def search_read(
        self,
        model: str,
        domain: list,
        fields: list[str],
        limit: int | None = None,
    ) -> list[dict[str, Any]]:
        self._check(model)
        self.calls.append((model, "search_read"))
        return [
            {field: row[field] for field in fields if field in row}
            for row in self.rows[model][:limit]
        ]


def _move(
    move_id: int,
    name: str,
    move_type: str,
    invoice_date: str,
    partner_id: int,
    *,
    reversed_id: int | None = None,
) -> dict[str, Any]:
    return {
        "id": move_id,
        "name": name,
        "move_type": move_type,
        "state": "posted",
        "invoice_date": invoice_date,
        "company_id": [1, "Esenssi"],
        "currency_id": [1, "EUR"],
        "partner_id": [partner_id, f"Cliente {partner_id}"],
        "amount_untaxed": 0,
        "amount_total": 0,
        "reversed_entry_id": [reversed_id, "original"] if reversed_id else False,
    }


def _line(
    line_id: int,
    move_id: int,
    product_id: int,
    quantity: float,
    price_unit: float,
    discount: float,
    subtotal: float,
) -> dict[str, Any]:
    return {
        "id": line_id,
        "move_id": [move_id, f"MOVE/{move_id}"],
        "product_id": [product_id, f"Product {product_id}"],
        "quantity": quantity,
        "price_unit": price_unit,
        "discount": discount,
        "price_subtotal": subtotal,
        "display_type": "product",
    }


def _valuation(
    row_id: int,
    product_id: int,
    unit_cost: float,
    create_date: str,
    *,
    company_id: int = 1,
) -> dict[str, Any]:
    return {
        "id": row_id,
        "product_id": [product_id, f"Product {product_id}"],
        "company_id": [company_id, f"Company {company_id}"],
        "quantity": 1,
        "unit_cost": unit_cost,
        "value": unit_cost,
        "create_date": create_date,
    }


def _identity(tenant_id: str, *, role: str = "admin") -> dict[str, str]:
    suffix = uuid4().hex
    user_id = f"di-user-{suffix}"
    db = SessionLocal()
    try:
        db.add(
            IdentityUser(
                id=user_id,
                email=f"{suffix}@example.test",
                display_name="Decision Intelligence operator",
            )
        )
        db.add(
            IdentityMembership(
                id=f"di-membership-{suffix}",
                tenant_id=tenant_id,
                user_id=user_id,
                role_name=role,
                status="active",
            )
        )
        db.commit()
    finally:
        db.close()
    return {"Authorization": f"Bearer {issue_token(user_id, tenant_id, 'di-auth')}"}


def _mount_transport(monkeypatch, transport: AnalyticalReadTransport) -> None:
    def connection_context(
        _service,
        *,
        tenant_id: str,
        connection_id: str,
        connector_id: str,
    ):
        assert connector_id == "odoo"
        return object(), ConnectorContext(
            tenant_id=tenant_id,
            connection_id=connection_id,
            services={"transport_factory": lambda _context: transport},
        )

    monkeypatch.setattr(
        ConnectorApplicationService,
        "connection_context",
        connection_context,
    )


def _snapshot_payload(**overrides: Any) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "connection_id": "odoo-staging",
        "company_ids": [1],
        "period_start": "2026-02-01",
        "period_end": "2026-02-28",
        "comparison_period_start": "2026-01-01",
        "comparison_period_end": "2026-01-31",
        "max_rows_per_model": 100,
        "minimum_cost_coverage": 0.8,
    }
    payload.update(overrides)
    return payload


def _create_snapshot(
    monkeypatch,
    *,
    transport: AnalyticalReadTransport,
    tenant_id: str,
) -> tuple[TestClient, dict[str, str], dict[str, Any]]:
    monkeypatch.setattr(settings, "auth_secret", "di-auth")
    init_db()
    _mount_transport(monkeypatch, transport)
    headers = _identity(tenant_id)
    client = TestClient(app)
    response = client.post(
        "/v1/decision-intelligence/snapshots",
        headers=headers,
        json=_snapshot_payload(),
    )
    assert response.status_code == 201, response.text
    return client, headers, response.json()


def test_snapshot_is_reproducible_read_only_evidence(monkeypatch):
    transport = AnalyticalReadTransport()
    _, _, snapshot = _create_snapshot(
        monkeypatch,
        transport=transport,
        tenant_id=f"di-ready-{uuid4().hex}",
    )

    assert snapshot["status"] == "ready"
    assert snapshot["currency"] == "EUR"
    assert snapshot["metric_definition_version"] == "margin-truth/1.0.0"
    assert snapshot["read_only"] is True
    assert len(snapshot["source_hash"]) == 64
    assert snapshot["data_quality"]["cost_coverage_rate"] == 1
    assert snapshot["data_quality"]["blocking_issues"] == []
    assert snapshot["extraction_manifest"]["_extraction"]["write_methods"] == []
    assert snapshot["extraction_manifest"]["stock.valuation.layer"]["available"] is True
    assert {method for _, method in transport.calls}.issubset(
        {"version", "authenticate", "fields_get", "search_count", "search_read"}
    )


def test_margin_metrics_refunds_bridge_and_idempotency(monkeypatch):
    client, headers, snapshot = _create_snapshot(
        monkeypatch,
        transport=AnalyticalReadTransport(),
        tenant_id=f"di-margin-{uuid4().hex}",
    )
    url = f"/v1/decision-intelligence/snapshots/{snapshot['id']}/margin-analysis"
    first = client.post(url, headers=headers, json={"tolerance": 0.01})
    second = client.post(url, headers=headers, json={"tolerance": 0.01})

    assert first.status_code == second.status_code == 201
    analysis = first.json()
    assert second.json()["id"] == analysis["id"]
    assert second.json()["content_hash"] == analysis["content_hash"]
    assert analysis["status"] == "ready"
    values = analysis["comparison_metrics"]["values"]
    current_values = analysis["current_metrics"]["values"]
    assert Decimal(values["net_revenue"]["value"]) == Decimal("810")
    assert Decimal(values["refunds"]["value"]) == Decimal("90")
    assert Decimal(values["cost_of_sales"]["value"]) == Decimal("540")
    assert Decimal(values["gross_margin"]["value"]) == Decimal("270")
    assert Decimal(current_values["net_revenue"]["value"]) == Decimal("1828")
    assert Decimal(current_values["refunds"]["value"]) == Decimal("160")
    assert Decimal(current_values["cost_of_sales"]["value"]) == Decimal("1240")
    assert Decimal(current_values["gross_margin"]["value"]) == Decimal("588")
    assert Decimal(analysis["margin_bridge"]["previous_margin"]) == Decimal("270")
    assert Decimal(analysis["margin_bridge"]["current_margin"]) == Decimal("588")
    assert Decimal(analysis["margin_bridge"]["residual"]) == Decimal("0")
    assert analysis["margin_bridge"]["balanced"] is True
    assert analysis["product_drivers"]["current"]
    assert analysis["customer_drivers"]["current"]


def test_insufficient_cost_coverage_blocks_margin_but_not_revenue(monkeypatch):
    client, headers, snapshot = _create_snapshot(
        monkeypatch,
        transport=AnalyticalReadTransport(
            missing_costs=True,
            unavailable_models={"stock.valuation.layer"},
        ),
        tenant_id=f"di-blocked-{uuid4().hex}",
    )
    assert snapshot["status"] == "blocked"
    assert "insufficient_cost_coverage" in snapshot["data_quality"]["blocking_issues"]
    assert snapshot["extraction_manifest"]["stock.valuation.layer"]["available"] is False

    response = client.post(
        f"/v1/decision-intelligence/snapshots/{snapshot['id']}/margin-analysis",
        headers=headers,
        json={},
    )
    assert response.status_code == 201
    analysis = response.json()
    assert analysis["status"] == "blocked"
    assert Decimal(analysis["current_metrics"]["values"]["net_revenue"]["value"]) == Decimal("1828")
    assert analysis["current_metrics"]["values"]["gross_margin"]["value"] is None
    assert analysis["margin_bridge"] == {}
    assert any("margin conclusions are blocked" in item for item in analysis["warnings"])


def test_missing_required_fields_and_truncation_block_snapshot(monkeypatch):
    transport = AnalyticalReadTransport(missing_fields={"account.move.line": {"price_subtotal"}})
    transport.rows["account.move"].append(
        _move(99, "INV/TRUNCATED", "out_invoice", "2026-02-25", 10)
    )
    monkeypatch.setattr(settings, "auth_secret", "di-auth")
    init_db()
    _mount_transport(monkeypatch, transport)
    headers = _identity(f"di-fields-{uuid4().hex}")
    response = TestClient(app).post(
        "/v1/decision-intelligence/snapshots",
        headers=headers,
        json=_snapshot_payload(max_rows_per_model=5),
    )
    assert response.status_code == 201
    quality = response.json()["data_quality"]
    assert "required_analytical_fields_missing" in quality["blocking_issues"]
    assert "extraction_truncated" in quality["blocking_issues"]
    assert response.json()["status"] == "blocked"


def test_mixed_currency_blocks_unconverted_aggregation(monkeypatch):
    transport = AnalyticalReadTransport()
    transport.rows["account.move"][3]["currency_id"] = [2, "USD"]
    transport.rows["res.currency"].append({"id": 2, "name": "USD", "symbol": "$"})
    _, _, snapshot = _create_snapshot(
        monkeypatch,
        transport=transport,
        tenant_id=f"di-currency-{uuid4().hex}",
    )

    assert snapshot["status"] == "blocked"
    assert snapshot["currency"] is None
    assert "mixed_currencies_without_conversion" in snapshot["data_quality"]["blocking_issues"]


def test_snapshot_and_analysis_are_tenant_scoped_and_immutable(monkeypatch):
    tenant_id = f"di-scope-{uuid4().hex}"
    client, _, snapshot = _create_snapshot(
        monkeypatch,
        transport=AnalyticalReadTransport(),
        tenant_id=tenant_id,
    )
    other_headers = _identity(f"di-other-{uuid4().hex}", role="viewer")
    response = client.get(
        f"/v1/decision-intelligence/snapshots/{snapshot['id']}",
        headers=other_headers,
    )
    assert response.status_code == 404

    db = SessionLocal()
    try:
        row = db.get(AnalyticalSnapshot, snapshot["id"])
        assert row is not None
        original_hash = row.source_hash
        row.source_hash = "mutated"
        with pytest.raises(ValueError, match="analytical_evidence_immutable"):
            db.commit()
        db.rollback()
        assert db.get(AnalyticalSnapshot, snapshot["id"]).source_hash == original_hash
    finally:
        db.close()


def test_invalid_or_overlapping_period_is_rejected_before_extraction(monkeypatch):
    transport = AnalyticalReadTransport()
    monkeypatch.setattr(settings, "auth_secret", "di-auth")
    init_db()
    _mount_transport(monkeypatch, transport)
    headers = _identity(f"di-period-{uuid4().hex}")
    client = TestClient(app)

    invalid = client.post(
        "/v1/decision-intelligence/snapshots",
        headers=headers,
        json=_snapshot_payload(period_start="2026-02-99"),
    )
    overlap = client.post(
        "/v1/decision-intelligence/snapshots",
        headers=headers,
        json=_snapshot_payload(comparison_period_end="2026-02-02"),
    )
    assert invalid.status_code == 400
    assert invalid.json()["detail"] == "invalid_analytical_period"
    assert overlap.status_code == 400
    assert overlap.json()["detail"] == "analytical_periods_must_not_overlap"
    assert transport.calls == []


def test_extraction_payload_keeps_cost_provenance_without_api_exposure(monkeypatch):
    client, headers, snapshot = _create_snapshot(
        monkeypatch,
        transport=AnalyticalReadTransport(),
        tenant_id=f"di-provenance-{uuid4().hex}",
    )
    assert "extraction_payload" not in snapshot

    db = SessionLocal()
    try:
        row = db.get(AnalyticalSnapshot, snapshot["id"])
        assert row is not None
        payload = json.loads(row.extraction_payload_json)
        sources = {line["cost"]["source"] for line in payload["lines"]}
        reliabilities = {line["cost"]["reliability"] for line in payload["lines"]}
        cost_by_line = {
            line["invoice_line_id"]: Decimal(line["cost"]["unit_cost"]) for line in payload["lines"]
        }
        assert sources == {"stock_valuation_layer"}
        assert reliabilities == {"high"}
        assert cost_by_line[101] == Decimal("60")
        assert cost_by_line[103] == Decimal("70")
    finally:
        db.close()

    fetched = client.get(
        f"/v1/decision-intelligence/snapshots/{snapshot['id']}",
        headers=headers,
    )
    assert fetched.status_code == 200
    assert "extraction_payload" not in fetched.json()
