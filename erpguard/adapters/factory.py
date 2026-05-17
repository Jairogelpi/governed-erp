import json

from pydantic import ValidationError

from erpguard.adapters.base import ERPAdapter
from erpguard.adapters.fake import FakeERPAdapter
from erpguard.adapters.odoo.adapter import OdooAdapter
from erpguard.adapters.odoo.config import OdooConfig
from erpguard.canonical.enums import ERPType
from erpguard.core.errors import AdapterConfigurationError, AdapterNotImplementedError
from erpguard.db.models import Connection


def get_adapter(erp_type: ERPType, config: dict | None = None) -> ERPAdapter:
    if erp_type is ERPType.FAKE:
        return FakeERPAdapter()
    if erp_type is ERPType.ODOO:
        if config is None:
            raise AdapterConfigurationError("Odoo adapter requires connection config.")
        try:
            return OdooAdapter(config=OdooConfig.model_validate(config))
        except ValidationError as exc:
            raise AdapterConfigurationError("Odoo adapter config is invalid.") from exc
    raise AdapterNotImplementedError(f"Adapter for ERP type '{erp_type.value}' is not implemented.")


def create_adapter_from_connection(connection: Connection) -> ERPAdapter:
    try:
        erp_type = ERPType(connection.erp_type)
    except ValueError as exc:
        raise AdapterConfigurationError(f"Connection '{connection.id}' has unsupported ERP type '{connection.erp_type}'.") from exc

    try:
        config = json.loads(connection.config_json)
    except json.JSONDecodeError as exc:
        raise AdapterConfigurationError(f"Connection '{connection.id}' has invalid JSON config.") from exc

    return get_adapter(erp_type, config=config)
