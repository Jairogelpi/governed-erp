from __future__ import annotations

from typing import Any

from erpguard.adapters.odoo.client import OdooClient
from erpguard.adapters.odoo.config import OdooConfig
from erpguard.adapters.odoo.readonly_client import OdooReadOnlyClient

PILOT_ALLOWED_WRITE_MODELS = frozenset({"mail.message"})
PILOT_ALLOWED_WRITE_METHODS = frozenset({"create"})


class PilotWriteViolationError(Exception):
    pass


class OdooPilotWriteClient(OdooReadOnlyClient):
    """Read-only client extended with mail.message.create only.

    Every other write model/method is blocked. This client is ONLY
    instantiated when ALLOW_R1_REAL_WRITE_PILOT=True.
    """

    def create(self, model: str, vals: dict[str, Any]) -> int:
        if model not in PILOT_ALLOWED_WRITE_MODELS:
            raise PilotWriteViolationError(
                f"Model '{model}' is not on the R1 pilot write whitelist. "
                f"Only {PILOT_ALLOWED_WRITE_MODELS} are allowed."
            )
        return int(self._client._execute_kw(model, "create", [vals], {}))


def build_pilot_write_client(config: OdooConfig) -> OdooPilotWriteClient:
    return OdooPilotWriteClient(OdooClient(config))
