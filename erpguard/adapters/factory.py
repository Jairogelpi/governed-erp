from erpguard.adapters.base import ERPAdapter
from erpguard.adapters.fake import FakeERPAdapter
from erpguard.canonical.enums import ERPType
from erpguard.core.errors import AdapterNotImplementedError


def get_adapter(erp_type: ERPType) -> ERPAdapter:
    if erp_type is ERPType.FAKE:
        return FakeERPAdapter()
    if erp_type is ERPType.ODOO:
        raise AdapterNotImplementedError("Adapter for ERP type 'odoo' is not implemented yet.")
    raise AdapterNotImplementedError(f"Adapter for ERP type '{erp_type.value}' is not implemented.")
