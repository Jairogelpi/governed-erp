"""Generate the Phase 11.5 Wave C0 repository inventory.

This is intentionally an inspection-only tool.  It uses Python AST analysis for
source inventories and imports the application only to capture the composed
route snapshot.  It does not move, delete, or mutate runtime code.
"""

from __future__ import annotations

import ast
import importlib
import json
import sys
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "artifacts" / "consolidation"
PRODUCTION_ROOTS = (ROOT / "apps", ROOT / "erpguard")
ALLOWED_CLASSIFICATIONS = {"keep", "migrate", "merge", "retire", "generated", "archive"}

PUBLIC_WHITELIST = [
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
    "/v1/evidence",
]

KEEP_MOVE_ROUTES = {
    "health.py",
    "identity.py",
    "unified_connections.py",
    "events.py",
    "processes.py",
    "variants.py",
    "candidates.py",
}
INTERNAL_ROUTES = {
    "demo.py",
    "recordings.py",
}
MIGRATE_ROUTES = {
    "skills.py",
    "approval_workflow.py",
    "execution_sandbox.py",
    "operator_evidence.py",
    "preflight.py",
    "audit.py",
    "record_to_skill.py",
    "skill_compilation.py",
    "skill_versioning.py",
    "active_skill_runner.py",
}
RETIRE_ROUTES = {
    "connections.py",
    "product.py",
    "live_read_sandbox.py",
    "write_readiness.py",
    "write_pilot.py",
    "r2_write_pilot.py",
    "r2_readiness.py",
    "platform_safety.py",
    "operator_flow.py",
    "release.py",
    "marketplace.py",
    "agent_builder.py",
    "agent_builder_advisory.py",
    "agent_proposal_drafts.py",
    "agent_clarifications.py",
    "agent_draft_bridge.py",
    "agent_draft_handoff.py",
    "agent_handoff_versioning.py",
    "agent_candidate_approval.py",
    "agent_candidate_decision.py",
    "agent_candidate_activation_request.py",
    "agent_candidate_activation.py",
    "agent_skill_run_preview.py",
    "operator_console.py",
    "operator_action_plan.py",
    "operator_action_dispatch.py",
    "operator_action_dispatch_execute.py",
    "manual_dry_run.py",
    "erp_adapter_capability.py",
    "erp_adapter_policy.py",
    "connector_setup.py",
    "connector_auth.py",
    "connector_credentials.py",
    "erp_fingerprinting.py",
    "safe_discovery.py",
    "generated_capabilities.py",
    "read_only_connector_activation.py",
    "odoo_read_only_adapter.py",
    "odoo_connection_test.py",
    "odoo_read_mapping.py",
    "odoo_read_evidence.py",
    "odoo_read_only_demo.py",
    "visual_browser_session.py",
    "visual_observation.py",
    "visual_workflow_trace.py",
    "visual_table_form_extraction.py",
    "external_connectors.py",
    "google_calendar_oauth.py",
    "skill_schedules.py",
    "odoo.py",
    "demo_dashboard.py",
}

DESTINATION_RULES = (
    ("candidate", "erpguard/evolution/candidates"),
    ("replay", "erpguard/evolution/replay"),
    ("proof", "erpguard/evolution/proofs"),
    ("process", "erpguard/domain/processes"),
    ("skill", "erpguard/domain/skills"),
    ("compil", "erpguard/compiler"),
    ("execution", "erpguard/runtime/deterministic"),
    ("permit", "erpguard/runtime/permits"),
    ("idempot", "erpguard/runtime/idempotency"),
    ("verif", "erpguard/runtime/verification"),
    ("approval", "erpguard/domain/approvals"),
    ("evidence", "erpguard/domain/evidence"),
    ("audit", "erpguard/domain/evidence"),
    ("orchestrat", "erpguard/application/services"),
    ("repository", "erpguard/infrastructure/persistence/repositories"),
    ("persist", "erpguard/infrastructure/persistence"),
)


@dataclass(frozen=True)
class SourceFile:
    path: Path
    module: str
    tree: ast.Module


def relative_name(path: Path) -> str:
    return path.relative_to(ROOT).as_posix()


def module_name(path: Path) -> str:
    relative = path.relative_to(ROOT).with_suffix("")
    parts = list(relative.parts)
    if parts[-1] == "__init__":
        parts.pop()
    return ".".join(parts)


def load_source_files() -> list[SourceFile]:
    files: list[SourceFile] = []
    for base in PRODUCTION_ROOTS:
        for path in sorted(base.rglob("*.py")):
            if "__pycache__" in path.parts:
                continue
            try:
                tree = ast.parse(path.read_text(encoding="utf-8-sig"), filename=str(path))
            except (OSError, SyntaxError) as exc:
                raise RuntimeError(f"cannot parse {relative_name(path)}: {exc}") from exc
            files.append(SourceFile(path, module_name(path), tree))
    return files


def literal_string(node: ast.AST | None) -> str | None:
    if node is None:
        return None
    try:
        value = ast.literal_eval(node)
    except (ValueError, TypeError):
        return None
    return value if isinstance(value, str) else None


def imported_modules(source: SourceFile, known_modules: set[str]) -> list[str]:
    result: set[str] = set()
    current_parts = source.module.split(".")
    for node in ast.walk(source.tree):
        if isinstance(node, ast.Import):
            result.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            if node.level:
                package = current_parts[:-1]
                if node.level > len(package) + 1:
                    base_parts: list[str] = []
                else:
                    base_parts = package[: len(package) - node.level + 1]
                if node.module:
                    base_parts.extend(node.module.split("."))
                base = ".".join(base_parts)
            else:
                base = node.module or ""
            for alias in node.names:
                candidate = ".".join(part for part in (base, alias.name) if part)
                if candidate in known_modules:
                    result.add(candidate)
                elif base:
                    result.add(base)
                else:
                    result.add(alias.name)
    return sorted(result)


def local_import_target(reference: str, known_modules: set[str]) -> str | None:
    parts = reference.split(".")
    for end in range(len(parts), 0, -1):
        candidate = ".".join(parts[:end])
        if candidate in known_modules:
            return candidate
    return None


def test_imports(path: Path, known_modules: set[str]) -> list[str]:
    try:
        tree = ast.parse(path.read_text(encoding="utf-8-sig"), filename=str(path))
    except (OSError, SyntaxError):
        return []
    source = SourceFile(path, module_name(path), tree)
    return imported_modules(source, known_modules)


def destination_for(name: str) -> str | None:
    lowered = name.lower()
    for token, destination in DESTINATION_RULES:
        if token in lowered:
            return destination
    return None


def route_classification(filename: str) -> tuple[str, str | None, str]:
    if filename in KEEP_MOVE_ROUTES:
        return "migrate", "apps/api/routes/public_v1", "explicit keep-and-move disposition"
    if filename in INTERNAL_ROUTES:
        return "keep", "apps/api/routes/internal", "explicit internal-tooling disposition"
    if filename in MIGRATE_ROUTES:
        return "migrate", "apps/api/routes/public_v1", "explicit behavior-migration disposition"
    if filename in RETIRE_ROUTES:
        return "retire", None, "explicit retirement disposition"
    return "retire", None, "not present in the retained public/internal route disposition"


def route_module_classification(source: SourceFile) -> tuple[str, str | None, str]:
    relative = relative_name(source.path)
    if "/public_v1/" in f"/{relative}":
        return "keep", "apps/api/routes/public_v1", "canonical C1 public route owner"
    if "/internal/" in f"/{relative}":
        return "keep", "apps/api/routes/internal", "canonical C1 internal route owner"
    return route_classification(source.path.name)


def parse_route_declarations(source: SourceFile) -> list[dict[str, Any]]:
    prefixes: dict[str, str] = {}
    for node in source.tree.body:
        if not isinstance(node, ast.Assign):
            continue
        if not isinstance(node.value, ast.Call) or not isinstance(node.value.func, ast.Name):
            continue
        if node.value.func.id != "APIRouter":
            continue
        prefix = next(
            (literal_string(keyword.value) for keyword in node.value.keywords if keyword.arg == "prefix"),
            "",
        )
        for target in node.targets:
            if isinstance(target, ast.Name):
                prefixes[target.id] = prefix or ""

    declarations: list[dict[str, Any]] = []
    methods = {"get", "post", "put", "patch", "delete", "options", "head", "trace"}
    for node in ast.walk(source.tree):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        for decorator in node.decorator_list:
            if not isinstance(decorator, ast.Call) or not isinstance(decorator.func, ast.Attribute):
                continue
            if not isinstance(decorator.func.value, ast.Name) or decorator.func.attr not in methods:
                continue
            router_name = decorator.func.value.id
            if router_name not in prefixes or not decorator.args:
                continue
            path = literal_string(decorator.args[0])
            if path is None:
                continue
            full_path = f"{prefixes[router_name].rstrip('/')}/{path.lstrip('/')}"
            if full_path == "//":
                full_path = "/"
            declarations.append(
                {
                    "method": decorator.func.attr.upper(),
                    "path": full_path,
                    "function": node.name,
                }
            )
    return sorted(declarations, key=lambda item: (item["path"], item["method"], item["function"]))


def source_graph(files: list[SourceFile]) -> tuple[dict[str, list[str]], dict[str, list[str]]]:
    known_modules = {source.module for source in files}
    imports: dict[str, list[str]] = {}
    imported_by: dict[str, list[str]] = defaultdict(list)
    for source in files:
        refs = imported_modules(source, known_modules)
        imports[source.module] = refs
        for ref in refs:
            target = local_import_target(ref, known_modules)
            if target and source.module not in imported_by[target]:
                imported_by[target].append(source.module)
    return imports, {key: sorted(value) for key, value in imported_by.items()}


def test_ownership(test_paths: list[Path], known_modules: set[str]) -> dict[str, list[str]]:
    owners: dict[str, list[str]] = defaultdict(list)
    for path in test_paths:
        for reference in test_imports(path, known_modules):
            target = local_import_target(reference, known_modules)
            if target and relative_name(path) not in owners[target]:
                owners[target].append(relative_name(path))
    return {key: sorted(value) for key, value in owners.items()}


def route_inventory(files: list[SourceFile]) -> tuple[list[dict[str, Any]], dict[str, list[str]]]:
    routes: list[dict[str, Any]] = []
    owners: dict[str, list[str]] = defaultdict(list)
    for source in files:
        if not relative_name(source.path).startswith("apps/api/routes/"):
            continue
        if source.path.name == "__init__.py":
            continue
        classification, destination, reason = route_module_classification(source)
        declarations = parse_route_declarations(source)
        item = {
            "path": relative_name(source.path),
            "module": source.module,
            "declared_routes": declarations,
            "classification": classification,
            "final_destination": destination,
            "deletion_wave": "C6" if classification == "retire" else ("C1" if destination else None),
            "reason": reason,
        }
        routes.append(item)
        for declaration in declarations:
            owners[source.module].append(f"{declaration['method']} {declaration['path']}")
    return sorted(routes, key=lambda item: item["path"]), {
        key: sorted(value) for key, value in owners.items()
    }


def model_inventory(files: list[SourceFile]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    models: list[dict[str, Any]] = []
    tables: list[dict[str, Any]] = []
    for source in files:
        for node in source.tree.body:
            if not isinstance(node, ast.ClassDef):
                continue
            bases = [ast.unparse(base) for base in node.bases]
            table_name: str | None = None
            for child in node.body:
                if isinstance(child, ast.Assign):
                    targets = child.targets
                elif isinstance(child, ast.AnnAssign):
                    targets = [child.target]
                else:
                    continue
                if any(isinstance(target, ast.Name) and target.id == "__tablename__" for target in targets):
                    value = child.value if isinstance(child, (ast.Assign, ast.AnnAssign)) else None
                    table_name = literal_string(value)
            if not table_name and not any(base == "Base" or base.endswith(".Base") for base in bases):
                continue
            is_bounded = "/model_packages/" in f"/{relative_name(source.path)}"
            classification = "keep" if is_bounded else "migrate"
            destination = (
                "erpguard/infrastructure/persistence/models"
                if not is_bounded
                else f"erpguard/infrastructure/persistence/models/{source.path.stem}"
            )
            model = {
                "model": node.name,
                "module": source.module,
                "path": relative_name(source.path),
                "bases": bases,
                "table": table_name,
                "bounded_context_owner": source.path.stem if is_bounded else "legacy_unbounded",
                "classification": classification,
                "final_destination": destination,
                "deletion_wave": "C5" if classification == "migrate" else None,
                "reason": "bounded model package" if is_bounded else "legacy model requires bounded-context ownership",
            }
            models.append(model)
            if table_name:
                tables.append(
                    {
                        "table": table_name,
                        "model": node.name,
                        "module": source.module,
                        "owner": model["bounded_context_owner"],
                        "classification": classification,
                        "final_destination": destination,
                        "deletion_wave": "C5" if classification == "migrate" else None,
                        "reason": model["reason"],
                    }
                )
    return sorted(models, key=lambda item: (item["path"], item["model"])), sorted(
        tables, key=lambda item: item["table"]
    )


def repository_inventory(files: list[SourceFile]) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    for source in files:
        if "repositories" not in source.path.parts and source.path.name != "repositories.py":
            continue
        for node in source.tree.body:
            if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            bounded = "infrastructure" in source.path.parts
            result.append(
                {
                    "function": node.name,
                    "module": source.module,
                    "path": relative_name(source.path),
                    "classification": "keep" if bounded else "migrate",
                    "final_destination": (
                        None
                        if bounded
                        else "erpguard/infrastructure/persistence/repositories"
                    ),
                    "deletion_wave": None if bounded else "C5",
                    "reason": "bounded repository" if bounded else "legacy repository monolith",
                }
            )
    return sorted(result, key=lambda item: (item["path"], item["function"]))


def docs_inventory() -> list[dict[str, Any]]:
    paths = sorted(
        path
        for path in ROOT.rglob("*.md")
        if ".git" not in path.parts and "__pycache__" not in path.parts
    )
    result: list[dict[str, Any]] = []
    for path in paths:
        relative = relative_name(path)
        lower = relative.lower()
        archived = any(token in lower for token in ("docs/archive/", "docs/legacy/", "docs/archive"))
        classification = "archive" if archived else "keep"
        result.append(
            {
                "path": relative,
                "title": next(
                    (
                        line.lstrip("# ").strip()
                        for line in path.read_text(encoding="utf-8-sig").splitlines()
                        if line.startswith("#")
                    ),
                    None,
                ),
                "classification": classification,
                "final_destination": "docs/archive" if archived else None,
                "deletion_wave": "C7" if archived else None,
                "reason": "historical release/archive path" if archived else "current documentation entry point",
            }
        )
    return result


def production_module_inventory(
    files: list[SourceFile],
    imports: dict[str, list[str]],
    imported_by: dict[str, list[str]],
    route_owners: dict[str, list[str]],
    test_owners: dict[str, list[str]],
) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    for source in files:
        relative = relative_name(source.path)
        if relative.startswith("apps/api/routes/") and source.path.name != "__init__.py":
            classification, destination, reason = route_module_classification(source)
            deletion_wave = "C6" if classification == "retire" else "C1"
        elif relative.startswith("erpguard/product/"):
            has_external_importer = any(
                not importer.startswith("erpguard.product")
                for importer in imported_by.get(source.module, [])
            )
            classification = "migrate" if has_external_importer else "retire"
            destination = destination_for(source.module) if classification == "migrate" else None
            deletion_wave = "C4" if classification == "migrate" else "C6"
            reason = (
                "referenced by production code outside erpguard.product"
                if has_external_importer
                else "product module has no production importer outside erpguard.product"
            )
        elif relative in {"erpguard/db/models.py", "erpguard/db/repositories.py"}:
            classification = "migrate"
            destination = "erpguard/infrastructure/persistence"
            deletion_wave = "C5"
            reason = "legacy persistence monolith"
        elif relative.startswith("erpguard/adapters/"):
            classification = "retire"
            destination = None
            deletion_wave = "C2"
            reason = "legacy adapter path outside Connector SDK v2"
        else:
            classification = "keep"
            destination = None
            deletion_wave = None
            reason = "active non-legacy production module retained during C0"
        result.append(
            {
                "module": source.module,
                "path": relative,
                "imports": imports.get(source.module, []),
                "imported_by": sorted(imported_by.get(source.module, [])),
                "route_owners": route_owners.get(source.module, []),
                "tests": test_owners.get(source.module, []),
                "classification": classification,
                "final_destination": destination,
                "deletion_wave": deletion_wave,
                "reason": reason,
            }
        )
    return sorted(result, key=lambda item: item["path"])


def route_snapshot() -> list[dict[str, Any]]:
    sys.path.insert(0, str(ROOT))
    app = importlib.import_module("apps.api.main").app
    result: list[dict[str, Any]] = []

    def flatten(routes: list[Any], prefix: str = ""):
        for route in routes:
            original_router = getattr(route, "original_router", None)
            if original_router is not None:
                context = getattr(route, "include_context", None)
                child_prefix = prefix + (getattr(context, "prefix", "") or "")
                yield from flatten(original_router.routes, child_prefix)
                continue
            yield route, prefix

    for route, prefix in flatten(app.routes):
        path = getattr(route, "path", None)
        methods = getattr(route, "methods", None)
        endpoint = getattr(route, "endpoint", None)
        if not path or not methods or endpoint is None:
            continue
        full_path = f"{prefix.rstrip('/')}/{path.lstrip('/')}" if prefix else path
        result.append(
            {
                "path": full_path,
                "methods": sorted(methods),
                "endpoint": getattr(endpoint, "__name__", None),
                "endpoint_module": getattr(endpoint, "__module__", None),
            }
        )
    return sorted(result, key=lambda item: (item["path"], item["methods"], item["endpoint_module"] or "", item["endpoint"] or ""))


def write_json(filename: str, value: Any) -> None:
    (OUTPUT / filename).write_text(
        json.dumps(value, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def main() -> None:
    OUTPUT.mkdir(parents=True, exist_ok=True)
    previous_manifest: dict[str, Any] = {}
    manifest_path = OUTPUT / "consolidation_manifest.json"
    if manifest_path.is_file():
        try:
            previous_manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            previous_manifest = {}
    files = load_source_files()
    known_modules = {source.module for source in files}
    imports, imported_by = source_graph(files)
    test_paths = sorted((ROOT / "tests").rglob("test_*.py"))
    test_owners = test_ownership(test_paths, known_modules)
    route_items, route_owners = route_inventory(files)
    models, tables = model_inventory(files)
    repositories = repository_inventory(files)
    tests = [
        {
            "path": relative_name(path),
            "imports": test_imports(path, known_modules),
            "owned_modules": sorted(
                module for module, paths in test_owners.items() if relative_name(path) in paths
            ),
            "classification": "keep",
            "final_destination": None,
            "deletion_wave": None,
            "reason": "retained for behavior-preserving consolidation; no test deletion in C0",
        }
        for path in test_paths
    ]
    tests.sort(key=lambda item: item["path"])
    docs = docs_inventory()
    modules = production_module_inventory(files, imports, imported_by, route_owners, test_owners)
    snapshot = route_snapshot()

    manifest = {
        "phase": "11.5",
        "wave": previous_manifest.get("wave", "C0"),
        "repository": ROOT.name,
        "inspection_only": True,
        "classification_values": sorted(ALLOWED_CLASSIFICATIONS),
        "public_route_whitelist": PUBLIC_WHITELIST,
        "counts": {
            "production_modules": len(modules),
            "route_modules": len(route_items),
            "sqlalchemy_models": len(models),
            "tables": len(tables),
            "repository_functions": len(repositories),
            "test_files": len(tests),
            "documentation_entries": len(docs),
            "observed_routes": len(snapshot),
        },
        "unresolved_review": {
            "routes_not_in_disposition": [
                item["path"]
                for item in route_items
                if item["reason"].startswith("not present")
            ],
            "legacy_product_modules_without_destination": [
                item["module"]
                for item in modules
                if item["path"].startswith("erpguard/product/")
                and item["classification"] == "migrate"
                and item["final_destination"] is None
            ],
        },
        "verification": previous_manifest.get(
            "verification",
            {
                "regression": "not run by inventory generator",
                "alembic_upgrade": "not run by inventory generator",
                "route_snapshot": "captured from apps.api.main",
            },
        ),
    }

    write_json("consolidation_manifest.json", manifest)
    write_json("product_module_inventory.json", [item for item in modules if item["path"].startswith("erpguard/product/")])
    write_json("route_inventory.json", route_items)
    write_json(
        "import_graph.json",
        {
            "nodes": [source.module for source in files],
            "edges": [
                {"source": source, "target": target, "local": target in known_modules}
                for source, refs in imports.items()
                for target in refs
            ],
            "imported_by": imported_by,
        },
    )
    write_json("model_table_inventory.json", {"models": models, "tables": tables})
    write_json("repository_inventory.json", repositories)
    write_json("test_inventory.json", tests)
    write_json("docs_inventory.json", docs)
    write_json(
        "public_route_snapshot.json",
        {
            "source": "apps.api.main:app",
            "public_route_whitelist": PUBLIC_WHITELIST,
            "routes": snapshot,
            "observed_v1_routes": [item for item in snapshot if item["path"].startswith("/v1/")],
        },
    )

    print(json.dumps(manifest["counts"], sort_keys=True))


if __name__ == "__main__":
    main()
