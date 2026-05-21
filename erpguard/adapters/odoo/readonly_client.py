from __future__ import annotations

from typing import Any

from erpguard.adapters.odoo.config import OdooConfig
from erpguard.adapters.odoo.client import OdooClient
from erpguard.core.errors import ReadOnlyViolationError

READ_ONLY_ALLOWED_METHODS = {
    "search_read",
    "read",
    "fields_get",
    "search_count",
}


class OdooReadOnlyClient:
    def __init__(self, client: OdooClient) -> None:
        self._client = client

    def version(self) -> dict[str, Any]:
        return self._client.version()

    def authenticate(self) -> int:
        return self._client.authenticate()

    def execute_kw(self, model: str, method: str, args: list, kwargs: dict | None = None) -> Any:
        if method not in READ_ONLY_ALLOWED_METHODS:
            raise ReadOnlyViolationError(f"Method '{method}' is not allowed in read-only Odoo mode.")
        return self._client._execute_kw(model, method, args, kwargs or {})

    def search_read(self, model: str, domain: list, fields: list[str], limit: int | None = None) -> list[dict]:
        kwargs: dict[str, Any] = {"fields": fields}
        if limit is not None:
            kwargs["limit"] = limit
        return self.execute_kw(model, "search_read", [domain], kwargs)

    def read(self, model: str, ids: list[int], fields: list[str]) -> list[dict]:
        return self.execute_kw(model, "read", [ids], {"fields": fields})

    def fields_get(self, model: str, attributes: list[str] | None = None) -> dict:
        kwargs: dict[str, Any] = {}
        if attributes is not None:
            kwargs["attributes"] = attributes
        return self.execute_kw(model, "fields_get", [], kwargs)

    def search_count(self, model: str, domain: list) -> int:
        return int(self.execute_kw(model, "search_count", [domain], {}))


def build_readonly_client(config: OdooConfig) -> OdooReadOnlyClient:
    return OdooReadOnlyClient(OdooClient(config))
