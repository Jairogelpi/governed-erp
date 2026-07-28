# Phase 11.5 Wave C0 — Consolidation Inventory

Status: current inspection artifact; no runtime relocation or deletion has been performed.

## Result

The repository was inspected with `scripts/generate_consolidation_inventory.py`.
The generator uses Python AST analysis for source, import, model, repository,
test and documentation inventories, and recursively inspects the FastAPI
composition root for the route snapshot.

| Area | Count |
| --- | ---: |
| Production modules | 514 |
| API route modules | 74 |
| SQLAlchemy models/tables | 150 / 150 |
| Legacy repository functions | 369 |
| Test files | 406 |
| Markdown documentation entries | 97 |
| Observed composed routes | 396 |

Machine-readable outputs are under `artifacts/consolidation/`:

- `consolidation_manifest.json` — phase, counts, whitelist, unresolved review and verification status;
- `product_module_inventory.json` — every `erpguard.product` module with AST import ownership;
- `route_inventory.json` — route declarations and disposition evidence;
- `import_graph.json` — production import edges and reverse ownership;
- `model_table_inventory.json` — model/table ownership and persistence destination;
- `repository_inventory.json` — repository function inventory;
- `test_inventory.json` — test files and imported module ownership;
- `docs_inventory.json` — documentation entry points and archive classification;
- `public_route_snapshot.json` — current `apps.api.main:app` route snapshot.

## Verification

```text
python -m ruff check scripts/generate_consolidation_inventory.py tests/test_phase115_consolidation_inventory.py
python -m pytest tests/test_phase115_consolidation_inventory.py tests/test_phase11_candidate_branching.py tests/test_phase11_candidate_evidence.py tests/test_phase11_candidate_migration.py -q
python -m alembic upgrade head  # temporary SQLite database
```

The focused slice passed with 12 tests. The clean migration reached
`0008_candidate_integrity`. The full repository suite was intentionally not run
in this continuation, so its status remains pending.

## Findings carried into C1

- The default app still mounts the legacy/experimental route set; the snapshot
  records 396 effective routes, while the target whitelist has 14 route roots.
- `erpguard/product` remains active and contains 269 modules; the inventory
  records production importers, route owners, test owners and unresolved
  destination reviews rather than guessing a bulk deletion.
- Persistence is still split between bounded model packages and the legacy
  `erpguard.db.models`/`erpguard.db.repositories` monoliths.
- C0 made no runtime behavior change. The next safe wave is C1: introduce the
  composition root and public/internal route boundaries behind tests.
