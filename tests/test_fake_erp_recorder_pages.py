from __future__ import annotations

from fastapi.testclient import TestClient

from apps.api.main import app

client = TestClient(app)

_RSID = "ui_session_test_sprint21"


def test_orders_page_without_rsid_has_no_recorder_overlay():
    r = client.get("/fake-erp/sales/orders")
    assert r.status_code == 200
    assert "erpguard-recorder-overlay" not in r.text
    assert "erpguard-recorder-s21" not in r.text


def test_orders_page_with_rsid_injects_recorder_script():
    r = client.get(f"/fake-erp/sales/orders?rsid={_RSID}")
    assert r.status_code == 200
    assert "erpguard-recorder-s21" in r.text
    assert "erpguard-recorder-overlay" in r.text
    assert _RSID in r.text


def test_orders_page_recorder_has_correct_endpoint():
    r = client.get(f"/fake-erp/sales/orders?rsid={_RSID}")
    body = r.text
    # endpoint is constructed dynamically: apiBase + "/v1/record-to-skill/sessions/" + rsid + "/events"
    assert "/v1/record-to-skill/sessions/" in body
    assert "events" in body
    assert _RSID in body


def test_orders_page_recorder_has_finish_endpoint():
    r = client.get(f"/fake-erp/sales/orders?rsid={_RSID}")
    body = r.text
    # finish endpoint is constructed dynamically
    assert "/v1/record-to-skill/sessions/" in body
    assert "finish" in body
    assert _RSID in body


def test_orders_page_has_accessible_search_input():
    r = client.get("/fake-erp/sales/orders")
    assert 'aria-label="Search orders"' in r.text
    assert 'role="search"' in r.text
    assert 'data-testid="order-search"' in r.text


def test_orders_page_open_order_links_have_aria_label():
    r = client.get("/fake-erp/sales/orders")
    assert 'aria-label="Open order SO-VALID"' in r.text


def test_orders_page_rsid_propagates_to_order_links():
    r = client.get(f"/fake-erp/sales/orders?rsid={_RSID}")
    assert f"rsid={_RSID}" in r.text


def test_order_detail_without_rsid_has_no_recorder():
    r = client.get("/fake-erp/sales/orders/SO-VALID")
    assert "erpguard-recorder-s21" not in r.text


def test_order_detail_with_rsid_injects_recorder():
    r = client.get(f"/fake-erp/sales/orders/SO-VALID?rsid={_RSID}")
    assert "erpguard-recorder-s21" in r.text
    assert _RSID in r.text


def test_order_detail_formula_tab_has_aria_label():
    r = client.get("/fake-erp/sales/orders/SO-VALID")
    assert 'data-testid="formula-tab"' in r.text
    assert 'aria-label="Formula tab"' in r.text


def test_order_detail_rsid_propagates_to_formula_link():
    r = client.get(f"/fake-erp/sales/orders/SO-VALID?rsid={_RSID}")
    assert f"rsid={_RSID}" in r.text


def test_formula_page_without_rsid_has_no_recorder():
    r = client.get("/fake-erp/sales/orders/SO-VALID/formula")
    assert "erpguard-recorder-s21" not in r.text


def test_formula_page_with_rsid_injects_recorder():
    r = client.get(f"/fake-erp/sales/orders/SO-VALID/formula?rsid={_RSID}")
    assert "erpguard-recorder-s21" in r.text
    assert _RSID in r.text


def test_formula_page_review_button_has_accessible_attrs():
    r = client.get("/fake-erp/sales/orders/SO-VALID/formula")
    assert 'data-testid="review-formula"' in r.text
    assert 'aria-label="Review formula"' in r.text
    assert 'name="review-formula"' in r.text


def test_existing_tests_not_broken_orders():
    r = client.get("/fake-erp/sales/orders")
    assert r.status_code == 200
    assert 'data-testid="order-search"' in r.text
    assert 'data-testid="open-order-SO-VALID"' in r.text


def test_existing_tests_not_broken_formula():
    r = client.get("/fake-erp/sales/orders/SO-VALID/formula")
    assert r.status_code == 200
    assert 'data-testid="formula-status"' in r.text
    assert 'data-testid="review-formula"' in r.text
