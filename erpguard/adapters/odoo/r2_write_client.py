from __future__ import annotations

from typing import Any

from erpguard.adapters.odoo.client import OdooClient
from erpguard.adapters.odoo.config import OdooConfig
from erpguard.adapters.odoo.readonly_client import OdooReadOnlyClient

R2_ALLOWED_WRITE_MODELS = frozenset({"res.partner"})
R2_ALLOWED_WRITE_FIELDS = frozenset({"comment", "website"})


class R2WriteViolationError(Exception):
    pass


class OdooR2WriteClient(OdooReadOnlyClient):
    """Read-only client extended with res.partner.write on allowed fields only.

    Only instantiated when ALLOW_R2_REAL_WRITE_PILOT=True and environment is staging/demo.
    """

    def write(self, model: str, record_id: int, vals: dict[str, Any]) -> bool:
        if model not in R2_ALLOWED_WRITE_MODELS:
            raise R2WriteViolationError(
                f"Model '{model}' is not on the R2 pilot write whitelist. "
                f"Only {sorted(R2_ALLOWED_WRITE_MODELS)} are allowed."
            )
        disallowed = set(vals.keys()) - R2_ALLOWED_WRITE_FIELDS
        if disallowed:
            raise R2WriteViolationError(
                f"Fields {sorted(disallowed)} are not on the R2 allowed field list. "
                f"Only {sorted(R2_ALLOWED_WRITE_FIELDS)} are allowed."
            )
        return bool(self._client._execute_kw(model, "write", [[record_id], vals], {}))

    def read_fields(self, model: str, record_id: int, fields: list[str]) -> dict[str, Any]:
        if model not in R2_ALLOWED_WRITE_MODELS:
            raise R2WriteViolationError(f"Cannot snapshot model '{model}'.")
        rows = self._client._execute_kw(model, "read", [[record_id], fields], {})
        if not rows:
            return {}
        return {k: v for k, v in rows[0].items() if k in fields}


def build_r2_write_client(config: OdooConfig) -> OdooR2WriteClient:
    return OdooR2WriteClient(OdooClient(config))
