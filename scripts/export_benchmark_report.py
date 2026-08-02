"""Spec 93/95 -- run a real ERPRiskBench `BenchmarkRun` against a scratch
database and export its generated report + raw case results to disk.

This exists so the TFM memory (Spec 95 Sec 39.1's "Experiment and results"
chapter, `docs/tfm/memoria_draft.md`) can cite a real `BenchmarkRun` id and
a real report artifact path instead of hand-restating numbers -- the same
"report generated from data, not edited manually" discipline
`erpguard/benchmark/report.py` already enforces on itself.

`direct_tool_agent` is intentionally excluded from the default run: it
requires `ANTHROPIC_API_KEY` and `ERPGUARD_ALLOW_BENCHMARK_DIRECT_AGENT=true`,
neither of which is assumed to be configured wherever this script runs.
Without them every case would honestly report `final_state="not_run"`,
which is correct but not informative -- pass `--include-direct-agent` to
force it if you have the key configured.

Usage:
    python scripts/export_benchmark_report.py [--include-direct-agent] [--out docs/benchmark/reports]

Uses a throwaway SQLite database (deleted after export) so it never
touches whatever `ERPGUARD_DATABASE_URL` the caller's shell has set.
"""
from __future__ import annotations

import argparse
import json
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset-version", default="quote_to_order_v1_seed92")
    parser.add_argument("--repeats", type=int, default=1)
    parser.add_argument("--include-direct-agent", action="store_true")
    parser.add_argument("--out", type=Path, default=Path("docs/benchmark/reports"))
    args = parser.parse_args()

    configurations = ["fixed_workflow", "erpguard_candidate"]
    if args.include_direct_agent:
        configurations.append("direct_tool_agent")

    with tempfile.TemporaryDirectory() as tmp:
        db_path = Path(tmp) / "benchmark_export.db"
        import os

        os.environ["ERPGUARD_DATABASE_URL"] = f"sqlite:///{db_path}"

        from alembic import command
        from alembic.config import Config

        alembic_cfg = Config(str(Path(__file__).resolve().parents[1] / "alembic.ini"))
        command.upgrade(alembic_cfg, "head")

        # Import after ERPGUARD_DATABASE_URL is set so the engine binds to
        # the scratch database, not whatever the caller's env already had.
        from erpguard.application.benchmark.service import BenchmarkService
        from erpguard.db.session import SessionLocal

        session = SessionLocal()
        try:
            service = BenchmarkService(session)
            run = service.create_run(
                tenant_id="tfm_export",
                dataset_version=args.dataset_version,
                configurations=configurations,
                repeats=args.repeats,
                created_by="scripts/export_benchmark_report.py",
            )
            report = service.report(tenant_id="tfm_export", run_id=run.id)

            from erpguard.db.model_packages.benchmark import BenchmarkCaseResult

            raw_rows = (
                session.query(BenchmarkCaseResult)
                .filter_by(tenant_id="tfm_export", benchmark_run_id=run.id)
                .all()
            )
            raw_results = [
                {
                    "id": row.id,
                    "configuration": row.configuration,
                    "case_id": row.case_id,
                    "category": row.category,
                    "repeat_index": row.repeat_index,
                    "outcome": json.loads(row.outcome_json),
                    "latency_ms": row.latency_ms,
                    "token_cost": row.token_cost,
                }
                for row in raw_rows
            ]
        finally:
            session.close()

    args.out.mkdir(parents=True, exist_ok=True)
    report_path = args.out / f"{run.id}.report.json"
    raw_path = args.out / f"{run.id}.raw_results.json"
    report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    raw_path.write_text(json.dumps(raw_results, indent=2), encoding="utf-8")

    print(f"BenchmarkRun id: {run.id}")
    print(f"Dataset version: {args.dataset_version}")
    print(f"Configurations: {configurations}")
    print(f"Report written to: {report_path}")
    print(f"Raw results written to: {raw_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
