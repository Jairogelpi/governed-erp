from erpguard.adapters.base import ERPAdapter
from erpguard.adapters.fake import FakeERPAdapter
from erpguard.adapters.odoo.adapter import OdooAdapter
from erpguard.adapters.odoo.config import OdooConfig
from erpguard.canonical.enums import ERPType
from erpguard.core.errors import AdapterConfigurationError, AdapterNotImplementedError


def get_adapter(erp_type: ERPType, config: dict | None = None) -> ERPAdapter:
    if erp_type is ERPType.FAKE:
        return FakeERPAdapter()
    if erp_type is ERPType.ODOO:
        if config is None:
            raise AdapterConfigurationError("Odoo adapter requires connection config.")
        return OdooAdapter(config=OdooConfig.model_validate(config))
    raise AdapterNotImplementedError(f"Adapter for ERP type '{erp_type.value}' is not implemented.")
