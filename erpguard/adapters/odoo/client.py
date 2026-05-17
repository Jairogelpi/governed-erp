import xmlrpc.client
from typing import Any

from erpguard.adapters.odoo.config import OdooConfig
from erpguard.core.errors import AdapterAuthenticationError


class OdooClient:
    def __init__(self, config: OdooConfig) -> None:
        self.config = config
        self._common = xmlrpc.client.ServerProxy(f"{config.url}/xmlrpc/2/common")
        self._models = xmlrpc.client.ServerProxy(f"{config.url}/xmlrpc/2/object")
        self._uid: int | None = None

    def version(self) -> dict[str, Any]:
        return self._common.version()

    def authenticate(self) -> int:
        uid = self._common.authenticate(
            self.config.database,
            self.config.username,
            self.config.api_key,
            {},
        )
        if not uid:
            raise AdapterAuthenticationError("Odoo authentication failed.")
        self._uid = int(uid)
        return self._uid

    def search_read(self, model: str, domain: list, fields: list[str], limit: int | None = None) -> list[dict]:
        kwargs: dict[str, Any] = {"fields": fields}
        if limit is not None:
            kwargs["limit"] = limit
        return self._execute_kw(model, "search_read", [domain], kwargs)

    def read(self, model: str, ids: list[int], fields: list[str]) -> list[dict]:
        return self._execute_kw(model, "read", [ids], {"fields": fields})

    def _execute_kw(self, model: str, method: str, args: list, kwargs: dict) -> Any:
        uid = self._uid if self._uid is not None else self.authenticate()
        return self._models.execute_kw(
            self.config.database,
            uid,
            self.config.api_key,
            model,
            method,
            args,
            kwargs,
        )
