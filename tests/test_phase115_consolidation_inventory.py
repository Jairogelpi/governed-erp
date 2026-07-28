from __future__ import annotations

import json
from pathlib import Path

from apps.api.app_factory import create_public_app


ROOT = Path(__file__).resolve().parents[1]
INVENTORY = ROOT / "artifacts" / "consolidation"
app = create_public_app(include_internal=False)


def _route_signature_from_app() -> list[dict[str, object]]:
    routes: list[dict[str, object]] = []

    def flatten(entries, prefix=""):
        for entry in entries:
            original_router = getattr(entry, "original_router", None)
            if original_router is not None:
                context = getattr(entry, "include_context", None)
                child_prefix = prefix + (getattr(context, "prefix", "") or "")
                yield from flatten(original_router.routes, child_prefix)
                continue
            yield entry, prefix

    for route, prefix in flatten(app.routes):
        path = getattr(route, "path", None)
        methods = getattr(route, "methods", None)
        endpoint = getattr(route, "endpoint", None)
        if not path or not methods or endpoint is None:
            continue
        routes.append(
            {
                "path": f"{prefix.rstrip('/')}/{path.lstrip('/')}" if prefix else path,
                "methods": sorted(methods),
                "endpoint": getattr(endpoint, "__name__", None),
                "endpoint_module": getattr(endpoint, "__module__", None),
            }
        )
    return sorted(
        routes,
        key=lambda item: (
            item["path"],
            item["methods"],
            item["endpoint_module"] or "",
            item["endpoint"] or "",
        ),
    )


def _read(name: str):
    return json.loads((INVENTORY / name).read_text(encoding="utf-8"))


def test_c0_inventory_artifacts_have_required_shape() -> None:
    manifest = _read("consolidation_manifest.json")
    assert manifest["phase"] == "11.5"
    assert manifest["wave"] in {"C0", "C1", "C2"}
    assert manifest["inspection_only"] is True
    assert set(manifest["classification_values"]) == {
        "keep",
        "migrate",
        "merge",
        "retire",
        "generated",
        "archive",
    }
    for filename in (
        "product_module_inventory.json",
        "route_inventory.json",
        "import_graph.json",
        "model_table_inventory.json",
        "repository_inventory.json",
        "test_inventory.json",
        "docs_inventory.json",
        "public_route_snapshot.json",
    ):
        assert (INVENTORY / filename).is_file(), filename


def test_every_inventory_item_has_a_valid_classification() -> None:
    allowed = set(_read("consolidation_manifest.json")["classification_values"])
    for filename in (
        "product_module_inventory.json",
        "route_inventory.json",
        "repository_inventory.json",
        "test_inventory.json",
        "docs_inventory.json",
    ):
        for item in _read(filename):
            assert item["classification"] in allowed, (filename, item)
    model_inventory = _read("model_table_inventory.json")
    for section in ("models", "tables"):
        for item in model_inventory[section]:
            assert item["classification"] in allowed, (section, item)


def test_public_route_snapshot_matches_composition_root() -> None:
    snapshot = _read("public_route_snapshot.json")
    assert snapshot["source"] == "apps.api.main:app"
    assert snapshot["routes"] == _route_signature_from_app()
