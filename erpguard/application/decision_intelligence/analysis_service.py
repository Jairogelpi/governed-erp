from __future__ import annotations

import json
from datetime import date
from decimal import Decimal
from typing import Any, Literal, cast
from uuid import uuid4

from sqlalchemy.orm import Session

from erpguard.db.model_packages.decision_intelligence import (
    AnalyticalSnapshot,
    DataQualityReport,
    MarginAnalysis,
)
from erpguard.domain.decision_intelligence.data_quality import evaluate_data_quality
from erpguard.domain.decision_intelligence.margin_bridge import calculate_margin_bridge
from erpguard.domain.decision_intelligence.metrics import calculate_period_metrics
from erpguard.domain.decision_intelligence.types import (
    DataQualityResult,
    ExtractionDataset,
    METRIC_DEFINITION_VERSION,
)
from erpguard.domain.processes.candidate_integrity import stable_digest

from .extraction_service import REQUIRED_FIELDS, OdooAnalyticalExtractor


class DecisionIntelligenceNotFound(KeyError):
    pass


class DecisionIntelligenceValidationError(ValueError):
    pass


def _dump(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"))


class DecisionIntelligenceService:
    def __init__(self, session: Session):
        self.session = session

    def create_snapshot(
        self,
        *,
        tenant_id: str,
        connection_id: str,
        company_ids: list[int],
        period_start: str,
        period_end: str,
        comparison_period_start: str,
        comparison_period_end: str,
        max_rows_per_model: int,
        minimum_cost_coverage: float,
        created_by: str,
        extractor: OdooAnalyticalExtractor,
    ) -> tuple[AnalyticalSnapshot, DataQualityReport]:
        try:
            (
                period_start_date,
                period_end_date,
                comparison_start_date,
                comparison_end_date,
            ) = (
                date.fromisoformat(period_start),
                date.fromisoformat(period_end),
                date.fromisoformat(comparison_period_start),
                date.fromisoformat(comparison_period_end),
            )
        except ValueError as exc:
            raise DecisionIntelligenceValidationError("invalid_analytical_period") from exc
        if period_start_date > period_end_date or comparison_start_date > comparison_end_date:
            raise DecisionIntelligenceValidationError("invalid_analytical_period")
        if not (comparison_end_date < period_start_date or period_end_date < comparison_start_date):
            raise DecisionIntelligenceValidationError("analytical_periods_must_not_overlap")
        dataset = extractor.extract(
            company_ids=company_ids,
            comparison_start=comparison_period_start,
            comparison_end=comparison_period_end,
            current_start=period_start,
            current_end=period_end,
            max_rows=max_rows_per_model,
        )
        quality = evaluate_data_quality(
            dataset,
            minimum_cost_coverage=minimum_cost_coverage,
        )
        missing_required_fields = {
            model: sorted(
                fields.intersection(dataset.manifest.get(model, {}).get("missing_fields", []))
            )
            for model, fields in REQUIRED_FIELDS.items()
        }
        missing_required_fields = {
            model: fields for model, fields in missing_required_fields.items() if fields
        }
        if missing_required_fields:
            quality = quality.model_copy(
                update={
                    "blocking_issues": sorted(
                        {
                            *quality.blocking_issues,
                            "required_analytical_fields_missing",
                        }
                    ),
                    "errors": [
                        *quality.errors,
                        "Required analytical fields are unavailable: "
                        + ", ".join(
                            f"{model}={','.join(fields)}"
                            for model, fields in sorted(missing_required_fields.items())
                        ),
                    ],
                    "confidence_grade": "blocked",
                }
            )
        truncated_models = sorted(
            model
            for model, item in dataset.manifest.items()
            if model != "_extraction" and item.get("truncated")
        )
        if truncated_models:
            quality = quality.model_copy(
                update={
                    "blocking_issues": sorted(
                        set([*quality.blocking_issues, "extraction_truncated"])
                    ),
                    "errors": [
                        *quality.errors,
                        f"Extraction truncated for: {', '.join(truncated_models)}.",
                    ],
                    "confidence_grade": "blocked",
                }
            )
        payload = dataset.model_dump(mode="json")
        source_hash = stable_digest(
            {
                "payload": payload,
                "metric_definition_version": METRIC_DEFINITION_VERSION,
                "periods": {
                    "current": [period_start, period_end],
                    "comparison": [comparison_period_start, comparison_period_end],
                },
                "company_ids": sorted(company_ids),
            }
        )
        snapshot = AnalyticalSnapshot(
            id=f"snapshot_{uuid4().hex}",
            tenant_id=tenant_id,
            connection_id=connection_id,
            company_ids_json=_dump(sorted(company_ids)),
            period_start=period_start,
            period_end=period_end,
            comparison_period_start=comparison_period_start,
            comparison_period_end=comparison_period_end,
            source_models_json=_dump(sorted(dataset.source_rows)),
            extraction_manifest_json=_dump(dataset.manifest),
            row_counts_json=_dump(dataset.row_counts),
            currency=dataset.currency,
            source_hash=source_hash,
            metric_definition_version=METRIC_DEFINITION_VERSION,
            extraction_payload_json=_dump(payload),
            status="blocked" if quality.blocking_issues else "ready",
            created_by=created_by,
        )
        quality_content = quality.model_dump(mode="json")
        report = DataQualityReport(
            id=f"dq_{uuid4().hex}",
            tenant_id=tenant_id,
            snapshot_id=snapshot.id,
            checks_json=_dump(quality_content["checks"]),
            errors_json=_dump(quality.errors),
            warnings_json=_dump(quality.warnings),
            cost_coverage_rate=quality.cost_coverage_rate,
            revenue_coverage_rate=quality.revenue_coverage_rate,
            duplicate_rate=quality.duplicate_rate,
            refund_reconciliation_rate=quality.refund_reconciliation_rate,
            confidence_grade=quality.confidence_grade,
            blocking_issues_json=_dump(quality.blocking_issues),
            content_hash=stable_digest(quality_content),
        )
        self.session.add_all([snapshot, report])
        self.session.commit()
        self.session.refresh(snapshot)
        self.session.refresh(report)
        return snapshot, report

    def get_snapshot(
        self,
        *,
        tenant_id: str,
        snapshot_id: str,
    ) -> tuple[AnalyticalSnapshot, DataQualityReport]:
        snapshot = (
            self.session.query(AnalyticalSnapshot)
            .filter_by(tenant_id=tenant_id, id=snapshot_id)
            .one_or_none()
        )
        if snapshot is None:
            raise DecisionIntelligenceNotFound("analytical_snapshot_not_found")
        report = (
            self.session.query(DataQualityReport)
            .filter_by(tenant_id=tenant_id, snapshot_id=snapshot_id)
            .one()
        )
        return snapshot, report

    def analyze_margin(
        self,
        *,
        tenant_id: str,
        snapshot_id: str,
        created_by: str,
        tolerance: Decimal = Decimal("0.01"),
    ) -> MarginAnalysis:
        existing = (
            self.session.query(MarginAnalysis)
            .filter_by(tenant_id=tenant_id, snapshot_id=snapshot_id)
            .one_or_none()
        )
        if existing is not None:
            return existing
        snapshot, report = self.get_snapshot(
            tenant_id=tenant_id,
            snapshot_id=snapshot_id,
        )
        dataset = ExtractionDataset.model_validate_json(snapshot.extraction_payload_json)
        quality = DataQualityResult(
            checks=json.loads(report.checks_json),
            errors=json.loads(report.errors_json),
            warnings=json.loads(report.warnings_json),
            cost_coverage_rate=report.cost_coverage_rate,
            revenue_coverage_rate=report.revenue_coverage_rate,
            duplicate_rate=report.duplicate_rate,
            refund_reconciliation_rate=report.refund_reconciliation_rate,
            confidence_grade=cast(
                Literal["A", "B", "C", "blocked"],
                report.confidence_grade,
            ),
            blocking_issues=json.loads(report.blocking_issues_json),
        )
        allow_margin = not quality.blocking_issues
        current = calculate_period_metrics(
            dataset.lines,
            start=snapshot.period_start,
            end=snapshot.period_end,
            quality=quality,
            allow_margin=allow_margin,
        )
        comparison = calculate_period_metrics(
            dataset.lines,
            start=snapshot.comparison_period_start,
            end=snapshot.comparison_period_end,
            quality=quality,
            allow_margin=allow_margin,
        )
        bridge = (
            calculate_margin_bridge(
                dataset.lines,
                comparison_start=snapshot.comparison_period_start,
                comparison_end=snapshot.comparison_period_end,
                current_start=snapshot.period_start,
                current_end=snapshot.period_end,
                tolerance=tolerance,
            ).model_dump(mode="json")
            if allow_margin
            else {}
        )
        warnings = list(quality.warnings)
        if not allow_margin:
            warnings.append("Revenue metrics are available, but margin conclusions are blocked.")
        content = {
            "snapshot_source_hash": snapshot.source_hash,
            "current": current.model_dump(mode="json"),
            "comparison": comparison.model_dump(mode="json"),
            "bridge": bridge,
            "warnings": warnings,
            "metric_definition_version": METRIC_DEFINITION_VERSION,
        }
        row = MarginAnalysis(
            id=f"analysis_{uuid4().hex}",
            tenant_id=tenant_id,
            snapshot_id=snapshot.id,
            status="blocked" if not allow_margin else "ready",
            metric_definition_version=METRIC_DEFINITION_VERSION,
            current_metrics_json=_dump(current.model_dump(mode="json")),
            comparison_metrics_json=_dump(comparison.model_dump(mode="json")),
            margin_bridge_json=_dump(bridge),
            product_drivers_json=_dump(
                {
                    "current": [item.model_dump(mode="json") for item in current.products],
                    "comparison": [item.model_dump(mode="json") for item in comparison.products],
                }
            ),
            customer_drivers_json=_dump(
                {
                    "current": [item.model_dump(mode="json") for item in current.customers],
                    "comparison": [item.model_dump(mode="json") for item in comparison.customers],
                }
            ),
            warnings_json=_dump(warnings),
            tolerance=float(tolerance),
            repeat_number=1,
            content_hash=stable_digest(content),
            created_by=created_by,
        )
        self.session.add(row)
        self.session.commit()
        self.session.refresh(row)
        return row

    def get_analysis(
        self,
        *,
        tenant_id: str,
        analysis_id: str,
    ) -> MarginAnalysis:
        row = (
            self.session.query(MarginAnalysis)
            .filter_by(tenant_id=tenant_id, id=analysis_id)
            .one_or_none()
        )
        if row is None:
            raise DecisionIntelligenceNotFound("margin_analysis_not_found")
        return row
