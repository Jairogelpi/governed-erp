from __future__ import annotations

from fastapi import FastAPI

from apps.api.app_factory import create_app, create_public_app


PUBLIC_ROOTS = {
    "/v1/health",
    "/v1/identity",
    "/v1/connections",
    "/v1/connectors",
    "/v1/events",
    "/v1/processes",
    "/v1/variants",
    "/v1/process-candidates",
    "/v1/replays",
    "/v1/proofs",
    "/v1/skills",
    "/v1/approvals",
    "/v1/executions",
    "/v1/runs",
    "/v1/evidence",
    "/v1/deployments",
    "/v1/decision-intelligence",
    "/v1/margin-analyses",
    "/v1/opportunities",
    "/v1/recommendations",
    "/v1/action-drafts",
    "/v1/canary-policies",
    "/v1/measurement-plans",
    "/v1/outcome-reports",
}


def _flatten(routes, prefix: str = ""):
    for route in routes:
        original_router = getattr(route, "original_router", None)
        if original_router is not None:
            context = getattr(route, "include_context", None)
            child_prefix = prefix + (getattr(context, "prefix", "") or "")
            yield from _flatten(original_router.routes, child_prefix)
            continue
        yield route, prefix


def _paths(app: FastAPI) -> set[str]:
    paths: set[str] = set()
    for route, prefix in _flatten(app.routes):
        path = getattr(route, "path", None)
        if path:
            paths.add(f"{prefix.rstrip('/')}/{path.lstrip('/')}" if prefix else path)
    return paths


def _is_public_path(path: str) -> bool:
    return any(path == root or path.startswith(root + "/") for root in PUBLIC_ROOTS)


def test_public_factory_mounts_only_whitelisted_api_roots() -> None:
    paths = _paths(create_public_app(include_internal=False))

    assert paths
    assert all(_is_public_path(path) for path in paths), sorted(paths)
    assert "/health" not in paths
    assert "/demo" not in paths
    assert "/fake-erp/sales/orders" not in paths
    assert not any(path.startswith("/docs") or path.startswith("/openapi") for path in paths)


def test_internal_surfaces_are_opt_in() -> None:
    public_paths = _paths(create_public_app(include_internal=False))
    internal_paths = _paths(create_public_app(include_internal=True))

    assert "/demo" not in public_paths
    assert "/demo" in internal_paths
    assert "/fake-erp/sales/orders" in internal_paths
    assert "/v1/recordings" in internal_paths


def test_default_create_app_is_public_only() -> None:
    public_paths = _paths(create_app(include_internal=False))

    assert "/v1/release/health" not in public_paths
    assert "/v1/agent-builder/sessions" not in public_paths
