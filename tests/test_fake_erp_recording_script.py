from fastapi.testclient import TestClient

from apps.api.main import app


client = TestClient(app)


def test_fake_erp_pages_without_recording_id_load_normally():
    response = client.get("/fake-erp/sales/orders")

    assert response.status_code == 200
    html = response.text
    assert "Fake ERP Sales Orders" in html
    assert "erpguard_human_recording_v0_2" not in html


def test_fake_erp_pages_with_recording_id_include_controlled_script_and_preserve_query_param():
    recording_id = "recording_test"

    orders_response = client.get(f"/fake-erp/sales/orders?recording_id={recording_id}")
    assert orders_response.status_code == 200
    orders_html = orders_response.text
    assert "erpguard_human_recording_v0_2" in orders_html
    assert "/v1/recordings/" in orders_html
    assert "recordingId" in orders_html
    assert "[data-testid='order-search']" in orders_html
    assert "[data-testid^='open-order-']" in orders_html
    assert f"recording_id={recording_id}" in orders_html

    detail_response = client.get(f"/fake-erp/sales/orders/SO-FORMULA-MISMATCH?recording_id={recording_id}")
    assert detail_response.status_code == 200
    detail_html = detail_response.text
    assert "[data-testid='formula-tab']" in detail_html
    assert f"/fake-erp/sales/orders/SO-FORMULA-MISMATCH/formula?recording_id={recording_id}" in detail_html

    formula_response = client.get(f"/fake-erp/sales/orders/SO-FORMULA-MISMATCH/formula?recording_id={recording_id}")
    assert formula_response.status_code == 200
    formula_html = formula_response.text
    assert "[data-testid='review-formula']" in formula_html
    assert "erpguard_human_recording_v0_2" in formula_html