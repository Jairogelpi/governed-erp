from __future__ import annotations

from collections.abc import Callable
from typing import Any, Protocol

from erpguard.core.errors import ReadOnlyViolationError


class OdooReadTransport(Protocol):
    def version(self) -> dict[str, Any]: ...

    def authenticate(self) -> int: ...

    def fields_get(self, model: str, attributes: list[str] | None = None) -> dict: ...

    def search_read(self, model: str, domain: list, fields: list[str], limit: int | None = None) -> list[dict]: ...

    def search_count(self, model: str, domain: list) -> int: ...


class LegacyXmlRpcReadTransport:
    """SDK transport adapter around the existing allowlisted XML-RPC client."""

    def __init__(self, client: OdooReadTransport):
        self._client = client

    def version(self) -> dict[str, Any]:
        return self._client.version()

    def authenticate(self) -> int:
        return self._client.authenticate()

    def fields_get(self, model: str, attributes: list[str] | None = None) -> dict:
        return self._client.fields_get(model, attributes)

    def search_read(self, model: str, domain: list, fields: list[str], limit: int | None = None) -> list[dict]:
        return self._client.search_read(model, domain, fields, limit)

    def search_count(self, model: str, domain: list) -> int:
        return self._client.search_count(model, domain)


class Json2ReadTransport:
    """JSON-2 read transport seam; the callback owns HTTP and credential resolution."""

    ALLOWED_METHODS = {"search_read", "read", "fields_get", "search_count", "version"}

    def __init__(self, caller: Callable[[str, str, dict[str, Any]], Any]):
        self._caller = caller

    def call(self, method: str, model: str, payload: dict[str, Any]) -> Any:
        if method not in self.ALLOWED_METHODS:
            raise ReadOnlyViolationError(f"Method '{method}' is not allowed in read-only Odoo JSON-2 mode.")
        return self._caller(method, model, payload)

    def version(self) -> dict[str, Any]:
        return self.call("version", "common", {})

    def authenticate(self) -> int:
        return 1

    def fields_get(self, model: str, attributes: list[str] | None = None) -> dict:
        return self.call("fields_get", model, {"attributes": attributes or []})

    def search_read(self, model: str, domain: list, fields: list[str], limit: int | None = None) -> list[dict]:
        payload: dict[str, Any] = {"domain": domain, "fields": fields}
        if limit is not None:
            payload["limit"] = limit
        return self.call("search_read", model, payload)

    def search_count(self, model: str, domain: list) -> int:
        return int(self.call("search_count", model, {"domain": domain}))
