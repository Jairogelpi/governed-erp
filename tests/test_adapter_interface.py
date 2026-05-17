import pytest

from erpguard.adapters.base import ERPAdapter
from erpguard.adapters.factory import get_adapter
from erpguard.adapters.fake import FakeERPAdapter
from erpguard.canonical.enums import CanonicalAction, ERPType
from erpguard.core.errors import AdapterConfigurationError


def test_factory_returns_fake_adapter():
    adapter = get_adapter(ERPType.FAKE)

    assert isinstance(adapter, FakeERPAdapter)
    assert isinstance(adapter, ERPAdapter)


def test_factory_requires_odoo_config():
    with pytest.raises(AdapterConfigurationError) as exc_info:
        get_adapter(ERPType.ODOO)

    assert "Odoo" in str(exc_info.value)


def test_fake_adapter_lists_supported_actions():
    adapter = get_adapter(ERPType.FAKE)

    assert adapter.list_supported_actions() == [
        CanonicalAction.INSPECT_SALES_ORDER,
        CanonicalAction.CONFIRM_SALES_ORDER,
        CanonicalAction.VALIDATE_FORMULA,
        CanonicalAction.INSPECT_ACCESS_RULES,
    ]
