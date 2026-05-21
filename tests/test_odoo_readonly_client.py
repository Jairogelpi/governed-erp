import pytest

from erpguard.adapters.odoo.readonly_client import READ_ONLY_ALLOWED_METHODS, OdooReadOnlyClient
from erpguard.core.errors import ReadOnlyViolationError


class FakeXmlRpcClient:
    def __init__(self):
        self.calls: list[tuple] = []

    def version(self):
        self.calls.append(("version",))
        return {"server_version": "19.0"}

    def authenticate(self):
        self.calls.append(("authenticate",))
        return 2

    def _execute_kw(self, model, method, args, kwargs):
        self.calls.append(("execute_kw", model, method, args, kwargs))
        if method == "search_read":
            return [{"id": 1, "name": "Demo"}]
        if method == "read":
            return [{"id": 1, "name": "Demo"}]
        if method == "fields_get":
            return {"name": {"type": "char"}}
        if method == "search_count":
            return 1
        return []


def test_readonly_client_allows_search_read():
    client = OdooReadOnlyClient(FakeXmlRpcClient())

    rows = client.search_read("sale.order", [], ["id", "name"], limit=1)

    assert rows[0]["name"] == "Demo"


def test_readonly_client_allows_read():
    client = OdooReadOnlyClient(FakeXmlRpcClient())

    rows = client.read("sale.order", [1], ["id", "name"])

    assert rows[0]["id"] == 1


def test_readonly_client_allows_fields_get():
    client = OdooReadOnlyClient(FakeXmlRpcClient())

    metadata = client.fields_get("sale.order", ["type"])

    assert metadata["name"]["type"] == "char"


def test_readonly_client_allows_search_count():
    client = OdooReadOnlyClient(FakeXmlRpcClient())

    assert client.search_count("sale.order", []) == 1


@pytest.mark.parametrize("method_name", sorted(READ_ONLY_ALLOWED_METHODS))
def test_readonly_client_execute_kw_allows_only_read_methods(method_name):
    client = OdooReadOnlyClient(FakeXmlRpcClient())

    client.execute_kw("sale.order", method_name, [], {})


@pytest.mark.parametrize(
    "method_name",
    ["create", "write", "unlink", "copy", "action_confirm", "button_validate", "action_post", "action_done", "action_assign"],
)
def test_readonly_client_blocks_forbidden_methods(method_name):
    client = OdooReadOnlyClient(FakeXmlRpcClient())

    with pytest.raises(ReadOnlyViolationError):
        client.execute_kw("sale.order", method_name, [], {})


def test_readonly_client_blocks_unknown_methods():
    client = OdooReadOnlyClient(FakeXmlRpcClient())

    with pytest.raises(ReadOnlyViolationError):
        client.execute_kw("sale.order", "unknown_method", [], {})
