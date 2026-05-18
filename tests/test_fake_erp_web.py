from fastapi.testclient import TestClient

from apps.api.main import app


client = TestClient(app)


def test_fake_erp_orders_page_loads():
    response = client.get("/fake-erp/sales/orders")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/html")
    assert "Fake ERP Sales Orders" in response.text
    assert 'data-testid="order-search"' in response.text
    assert 'data-testid="order-row-SO-VALID"' in response.text
    assert 'data-testid="open-order-SO-VALID"' in response.text


def test_fake_erp_valid_order_detail_loads():
    response = client.get("/fake-erp/sales/orders/SO-VALID")

    assert response.status_code == 200
    assert "SO-VALID" in response.text
    assert "Fake Customer" in response.text
    assert "draft" in response.text
    assert 'data-testid="formula-tab"' in response.text
    assert 'data-testid="order-status-result"' in response.text


def test_fake_erp_formula_page_loads_for_valid_order():
    response = client.get("/fake-erp/sales/orders/SO-VALID/formula")

    assert response.status_code == 200
    assert "Formula Tab - SO-VALID" in response.text
    assert "Mikado 100 ML" in response.text
    assert "Formula status" in response.text
    assert 'data-testid="formula-status"' in response.text
    assert 'data-testid="review-formula"' in response.text
    assert "Valid: formula matches product capacity" in response.text


def test_fake_erp_invalid_formula_data_is_visible():
    response = client.get("/fake-erp/sales/orders/SO-FORMULA-MISMATCH/formula")

    assert response.status_code == 200
    assert "Invalid: Formula ml per unit does not match product capacity." in response.text
    assert "Formula ml per unit:" in response.text
    assert "80" in response.text


def test_fake_erp_order_pages_are_deterministic():
    first = client.get("/fake-erp/sales/orders/SO-CAPACITY-NO-FORMULA")
    second = client.get("/fake-erp/sales/orders/SO-CAPACITY-NO-FORMULA")

    assert first.status_code == 200
    assert second.status_code == 200
    assert first.text == second.text
