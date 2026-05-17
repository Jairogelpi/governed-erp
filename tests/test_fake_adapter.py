import pytest

from erpguard.adapters.fake import FakeERPAdapter
from erpguard.canonical.enums import CanonicalAction, ERPType, SalesOrderState
from erpguard.canonical.objects import SalesOrder
from erpguard.core.errors import ObjectNotFoundError


def test_fake_adapter_health_check_works():
    adapter = FakeERPAdapter()

    assert adapter.get_erp_type() is ERPType.FAKE
    assert adapter.health_check() == {
        "status": "ok",
        "erp_type": "fake",
        "adapter": "FakeERPAdapter",
    }


def test_fake_adapter_returns_valid_sales_order():
    adapter = FakeERPAdapter()

    order = adapter.get_sales_order("so_valid")

    assert isinstance(order, SalesOrder)
    assert order.reference == "SO-VALID"
    assert order.state is SalesOrderState.DRAFT
    assert len(order.lines) == 1
    assert order.lines[0].product.capacity_ml == 100
    assert order.lines[0].formula_validation is not None
    assert order.lines[0].formula_validation.is_valid is True


def test_fake_adapter_returns_order_by_reference():
    adapter = FakeERPAdapter()

    order = adapter.get_sales_order_by_reference("SO-VALID")

    assert order.id == "so_valid"


def test_fake_adapter_returns_formula_mismatch_fixture():
    adapter = FakeERPAdapter()

    order = adapter.get_sales_order("so_formula_mismatch")

    assert order.reference == "SO-FORMULA-MISMATCH"
    assert order.lines[0].product.capacity_ml == 100
    assert order.lines[0].formula_validation is not None
    assert order.lines[0].formula_validation.is_valid is False
    assert order.lines[0].formula_validation.actual_ml_per_unit == 80


def test_fake_adapter_returns_empty_lines_fixture():
    adapter = FakeERPAdapter()

    order = adapter.get_sales_order("so_empty_lines")

    assert order.reference == "SO-EMPTY-LINES"
    assert order.lines == []


def test_fake_adapter_returns_capacity_without_formula_fixture():
    adapter = FakeERPAdapter()

    order = adapter.get_sales_order("so_capacity_no_formula")

    assert order.reference == "SO-CAPACITY-NO-FORMULA"
    assert order.lines[0].product.capacity_ml == 100
    assert order.lines[0].formula_lines == []
    assert order.lines[0].formula_validation is None


def test_fake_adapter_missing_order_raises_clear_domain_exception():
    adapter = FakeERPAdapter()

    with pytest.raises(ObjectNotFoundError) as exc_info:
        adapter.get_sales_order("missing")

    assert "SalesOrder" in str(exc_info.value)
    assert "missing" in str(exc_info.value)


def test_fake_adapter_inspect_permissions_returns_canonical_action_context():
    adapter = FakeERPAdapter()

    permissions = adapter.inspect_permissions(
        actor_id="actor_1",
        canonical_action=CanonicalAction.CONFIRM_SALES_ORDER,
        target_object="SalesOrder",
        target_id="so_valid",
    )

    assert permissions == {
        "actor_id": "actor_1",
        "canonical_action": "confirm_sales_order",
        "target_object": "SalesOrder",
        "target_id": "so_valid",
        "allowed": True,
        "source": "fake",
    }
