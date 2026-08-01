"""Spec 93 -- `BenchmarkService`: persists a `BenchmarkRun`, drives
`erpguard.benchmark.runner.run_benchmark`, and persists every
`BenchmarkCaseResult` row (append-only, Sec 28.4). Execution is
synchronous, not the background-job design the spec sketches (Sec
25.2's pattern) -- this codebase has no worker/queue infrastructure yet,
and the default (non-LLM) configurations run in well under a second for
120 cases, so a synchronous request/response is the honest simple
choice rather than adding new job infrastructure for its own sake. If
`direct_tool_agent` is enabled with a real API key and a large `repeats`,
the caller is explicitly opting into a slower request.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from sqlalchemy.orm import Session

from erpguard.benchmark.dataset import load_dataset
from erpguard.benchmark.report import generate_report
from erpguard.benchmark.runner import CONFIGURATIONS, run_benchmark
from erpguard.benchmark.types import CaseOutcome
from erpguard.db.model_packages.benchmark import BenchmarkCaseResult, BenchmarkRun


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


class BenchmarkRunNotFound(KeyError):
    pass


class BenchmarkValidationError(ValueError):
    pass


class BenchmarkService:
    def __init__(self, session: Session, *, dataset_dir: Path | None = None):
        self.session = session
        self.dataset_dir = dataset_dir or Path("docs/benchmark/datasets")

    def _get(self, *, tenant_id: str, run_id: str) -> BenchmarkRun:
        row = self.session.query(BenchmarkRun).filter_by(tenant_id=tenant_id, id=run_id).one_or_none()
        if row is None:
            raise BenchmarkRunNotFound(run_id)
        return row

    def get(self, *, tenant_id: str, run_id: str) -> BenchmarkRun:
        return self._get(tenant_id=tenant_id, run_id=run_id)

    def create_run(
        self, *, tenant_id: str, dataset_version: str, configurations: list[str],
        repeats: int, created_by: str,
    ) -> BenchmarkRun:
        unknown = set(configurations) - set(CONFIGURATIONS)
        if unknown:
            raise BenchmarkValidationError(f"unknown_benchmark_configurations:{sorted(unknown)}")
        if repeats < 1:
            raise BenchmarkValidationError("repeats_must_be_at_least_1")

        try:
            cases, manifest = load_dataset(self.dataset_dir, dataset_version)
        except FileNotFoundError as exc:
            raise BenchmarkValidationError(f"dataset_version_not_found:{dataset_version}") from exc

        run = BenchmarkRun(
            id=f"benchmarkrun_{uuid4().hex}",
            tenant_id=tenant_id,
            dataset_version=dataset_version,
            dataset_manifest_hash=manifest["dataset_hash"],
            configurations_json=json.dumps(sorted(configurations)),
            repeats=repeats,
            status="running",
            created_by=created_by,
        )
        self.session.add(run)
        self.session.commit()
        self.session.refresh(run)

        results = run_benchmark(cases=cases, configurations=configurations, repeats=repeats)
        for configuration, repeat_index, outcome in results:
            self.session.add(BenchmarkCaseResult(
                id=f"benchmarkresult_{uuid4().hex}",
                tenant_id=tenant_id,
                benchmark_run_id=run.id,
                configuration=configuration,
                case_id=outcome.case_id,
                category=outcome.category,
                repeat_index=repeat_index,
                outcome_json=outcome.model_dump_json(),
                latency_ms=outcome.latency_ms,
                token_cost=outcome.token_cost,
            ))
        run.status = "completed"
        run.completed_at = _utc_now()
        self.session.commit()
        self.session.refresh(run)
        return run

    def report(self, *, tenant_id: str, run_id: str) -> dict:
        run = self._get(tenant_id=tenant_id, run_id=run_id)
        rows = (
            self.session.query(BenchmarkCaseResult)
            .filter_by(tenant_id=tenant_id, benchmark_run_id=run_id)
            .all()
        )
        outcome_rows = [
            (row.configuration, row.repeat_index, CaseOutcome.model_validate_json(row.outcome_json))
            for row in rows
        ]
        return generate_report(outcome_rows, dataset_version=run.dataset_version)
