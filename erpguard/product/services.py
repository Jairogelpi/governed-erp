from __future__ import annotations

import json
from dataclasses import dataclass
from uuid import uuid4

from erpguard.adapters.odoo.config import OdooConfig
from erpguard.adapters.odoo.diagnosis import OdooDiagnosisService
from erpguard.adapters.odoo.readonly_client import build_readonly_client
from erpguard.core.errors import ObjectNotFoundError
from erpguard.db.models import Connection
from erpguard.db.repositories import (
    create_audit_event,
    create_automation_draft,
    create_business_signal,
    create_business_snapshot,
    create_opportunity,
    create_opportunity_scan,
    get_business_snapshot,
    get_connection,
    get_opportunity,
    get_opportunity_scan,
)
from erpguard.product.models import (
    AutomationDraftModel,
    BusinessAnalysisRequest,
    BusinessAnalysisResult,
    BusinessOpportunityModel,
    BusinessSignalModel,
    BusinessSnapshotModel,
    OpportunityROIModel,
    OpportunityScanModel,
)


@dataclass
class ProductAnalysisContext:
    connection: Connection
    config: OdooConfig


class BusinessSnapshotService:
    def __init__(self, context: ProductAnalysisContext, session) -> None:
        self.context = context
        self.session = session

    def capture(self, request: BusinessAnalysisRequest) -> BusinessSnapshotModel:
        diagnosis = OdooDiagnosisService(build_readonly_client(self.context.config), self.context.config).run(
            include_samples=request.include_samples,
            sample_limits=request.sample_limits.model_dump(),
        )
        row = create_business_snapshot(
            self.session,
            connection_id=self.context.connection.id,
            erp_type=self.context.connection.erp_type,
            snapshot_json=json.dumps(diagnosis, default=str),
            status=diagnosis.get("status", "ok"),
            read_only_mode=bool(diagnosis.get("read_only_mode", True)),
        )
        return BusinessSnapshotModel.model_validate(
            {
                "snapshot_id": row.id,
                "connection_id": row.connection_id,
                "status": row.status,
                "read_only_mode": row.read_only_mode,
                **diagnosis,
                "summary": {
                    "installed_modules": len(diagnosis.get("detected", {}).get("installed_modules", [])),
                    "core_models": len(diagnosis.get("detected", {}).get("core_models", [])),
                    "custom_fields": len(diagnosis.get("detected", {}).get("custom_fields", [])),
                },
                "created_at": row.created_at.isoformat(),
            }
        )


class SignalService:
    def __init__(self, context: ProductAnalysisContext, session) -> None:
        self.context = context
        self.session = session

    def derive(self, snapshot: BusinessSnapshotModel) -> list[BusinessSignalModel]:
        detected = snapshot.detected or {}
        warnings = {warning["code"]: warning for warning in snapshot.warnings}
        signals: list[BusinessSignalModel] = []

        modules = detected.get("installed_modules", [])
        if "sale" in modules:
            signals.append(
                self._persist_signal(
                    snapshot.snapshot_id,
                    "sales_module_present",
                    "Sales module available",
                    "info",
                    "Sales is installed, so read-only sales analysis and preflight planning are possible.",
                    70,
                    {"installed_modules": modules},
                )
            )
        if warnings.get("capacity_field_missing"):
            signals.append(
                self._persist_signal(
                    snapshot.snapshot_id,
                    "capacity_field_missing",
                    "Capacity field needs mapping",
                    "warning",
                    warnings["capacity_field_missing"]["message"],
                    95,
                    {"field": self.context.config.capacity_field, "detected_custom_fields": detected.get("custom_fields", [])},
                )
            )
        if warnings.get("formula_model_missing"):
            signals.append(
                self._persist_signal(
                    snapshot.snapshot_id,
                    "formula_model_missing",
                    "Formula model not confirmed",
                    "warning",
                    warnings["formula_model_missing"]["message"],
                    90,
                    {"formula_model": self.context.config.formula_model},
                )
            )
        if detected.get("sales_orders_sample_count", 0) > 0:
            signals.append(
                self._persist_signal(
                    snapshot.snapshot_id,
                    "sales_orders_sampled",
                    "Sales orders sampled",
                    "info",
                    f"Found {detected['sales_orders_sample_count']} sales order samples.",
                    60,
                    {"sales_orders_sample_count": detected.get("sales_orders_sample_count", 0)},
                )
            )
        if detected.get("products_sample_count", 0) > 0:
            signals.append(
                self._persist_signal(
                    snapshot.snapshot_id,
                    "products_sampled",
                    "Products sampled",
                    "info",
                    f"Found {detected['products_sample_count']} product samples.",
                    60,
                    {"products_sample_count": detected.get("products_sample_count", 0)},
                )
            )
        return signals

    def _persist_signal(
        self,
        snapshot_id: str,
        code: str,
        title: str,
        severity: str,
        message: str,
        score: int,
        evidence: dict,
    ) -> BusinessSignalModel:
        row = create_business_signal(
            self.session,
            business_snapshot_id=snapshot_id,
            signal_code=code,
            title=title,
            severity=severity,
            message=message,
            evidence_json=json.dumps(evidence, default=str),
            score=score,
        )
        return BusinessSignalModel.model_validate(
            {
                "signal_id": row.id,
                "code": row.signal_code,
                "title": row.title,
                "severity": row.severity,
                "message": row.message,
                "score": row.score,
                "evidence": evidence,
            }
        )


class ROIService:
    def score(self, opportunity_code: str, snapshot: BusinessSnapshotModel, signals: list[BusinessSignalModel]) -> OpportunityROIModel:
        detected = snapshot.detected or {}
        sales_orders = int(detected.get("sales_orders_sample_count", 0))
        products = int(detected.get("products_sample_count", 0))
        signal_codes = {signal.code for signal in signals}

        if opportunity_code == "formula_mapping_alignment":
            effort = 3.5
            savings = 4.0 + (1.0 if "capacity_field_missing" in signal_codes else 0.0) + (1.0 if "formula_model_missing" in signal_codes else 0.0)
            confidence = 0.92
            rationale = "Fixing mappings removes the current read-only validation gap and unlocks safer preflight planning."
        elif opportunity_code == "read_only_sales_preflight":
            effort = 8.0
            savings = max(2.5, sales_orders * 0.8)
            confidence = 0.78
            rationale = "A read-only sales preflight makes existing sales data easier to inspect before any future automation."
        elif opportunity_code == "product_metadata_governance":
            effort = 6.0
            savings = max(2.0, products * 0.6)
            confidence = 0.72
            rationale = "Standardizing product metadata keeps the product catalogue usable for future analysis and automation."
        else:
            effort = 5.0
            savings = 2.0
            confidence = 0.5
            rationale = "General business analysis opportunity based on the current Odoo snapshot."

        estimated_value = round(savings * 35.0, 2)
        payback_weeks = round((effort / max(savings, 0.5)) * 4.0, 1)
        score = min(100, int(round((savings / effort) * 25 + confidence * 35 + 25)))
        return OpportunityROIModel(
            implementation_effort_hours=round(effort, 1),
            estimated_monthly_savings_hours=round(savings, 1),
            estimated_monthly_value_eur=estimated_value,
            payback_weeks=payback_weeks,
            confidence=round(confidence, 2),
            score=score,
            rationale=rationale,
        )


class OpportunityScannerService:
    def __init__(self, context: ProductAnalysisContext, session, roi_service: ROIService | None = None) -> None:
        self.context = context
        self.session = session
        self.roi_service = roi_service or ROIService()

    def scan(
        self,
        snapshot: BusinessSnapshotModel,
        signals: list[BusinessSignalModel],
        max_opportunities: int,
    ) -> tuple[OpportunityScanModel, list[BusinessOpportunityModel], dict[str, float | int | str]]:
        detected = snapshot.detected or {}
        signal_codes = {signal.code for signal in signals}

        opportunity_specs: list[dict] = []
        if "capacity_field_missing" in signal_codes or "formula_model_missing" in signal_codes:
            opportunity_specs.append(
                {
                    "code": "formula_mapping_alignment",
                    "title": "Align formula field mappings",
                    "description": "Confirm the formula model and capacity field mappings so read-only business analysis can move from warnings to a reliable baseline.",
                    "recommendation": "Correct the Odoo field mappings and rerun the analysis before any future automation.",
                    "category": "data-governance",
                    "priority": 1,
                    "signal_codes": sorted(code for code in ["capacity_field_missing", "formula_model_missing"] if code in signal_codes),
                    "evidence": {
                        "warnings": [signal.code for signal in signals if signal.code in {"capacity_field_missing", "formula_model_missing"}],
                        "configured_capacity_field": self.context.config.capacity_field,
                        "configured_formula_model": self.context.config.formula_model,
                    },
                }
            )
        if "sale" in detected.get("installed_modules", []):
            opportunity_specs.append(
                {
                    "code": "read_only_sales_preflight",
                    "title": "Introduce read-only sales preflight",
                    "description": "Build a read-only sales-order inspection flow that can score and explain sales records before any write capability is considered.",
                    "recommendation": "Use the current Odoo connection to expose a read-only preflight view for sales orders.",
                    "category": "workflow-visibility",
                    "priority": 2,
                    "signal_codes": ["sales_module_present"],
                    "evidence": {"sales_orders_sample_count": detected.get("sales_orders_sample_count", 0)},
                }
            )
        if detected.get("products_sample_count", 0) > 0:
            opportunity_specs.append(
                {
                    "code": "product_metadata_governance",
                    "title": "Standardize product metadata",
                    "description": "Use the read-only sample data to normalize product metadata and make capacity mapping more reliable for future automations.",
                    "recommendation": "Review product fields and data quality before expanding the automation scope.",
                    "category": "catalog-governance",
                    "priority": 3,
                    "signal_codes": ["products_sampled"],
                    "evidence": {"products_sample_count": detected.get("products_sample_count", 0)},
                }
            )

        scan_row = create_opportunity_scan(
            self.session,
            business_snapshot_id=snapshot.snapshot_id,
            connection_id=snapshot.connection_id,
            status="completed",
            summary_json=json.dumps({"opportunity_count": 0, "signal_count": len(signals), "roi_score_average": 0}, default=str),
        )

        opportunities: list[BusinessOpportunityModel] = []
        for spec in opportunity_specs[:max_opportunities]:
            opportunities.append(self._persist_opportunity(scan_row.id, snapshot, spec, signals))

        roi_summary = self._build_roi_summary(opportunities)
        scan_row.summary_json = json.dumps(
            {
                "opportunity_count": len(opportunities),
                "signal_count": len(signals),
                "roi_score_average": roi_summary.get("average_score", 0),
            },
            default=str,
        )
        self.session.commit()
        self.session.refresh(scan_row)
        scan = OpportunityScanModel.model_validate(
            {
                "scan_id": scan_row.id,
                "snapshot_id": scan_row.business_snapshot_id,
                "connection_id": scan_row.connection_id,
                "status": scan_row.status,
                "opportunity_count": len(opportunities),
                "signal_count": len(signals),
                "roi_summary": roi_summary,
                "created_at": scan_row.created_at.isoformat(),
            }
        )
        return scan, opportunities, roi_summary

    def _persist_opportunity(
        self,
        scan_id: str,
        snapshot: BusinessSnapshotModel,
        spec: dict,
        signals: list[BusinessSignalModel],
    ) -> BusinessOpportunityModel:
        roi = self.roi_service.score(spec["code"], snapshot, signals)
        row = create_opportunity(
            self.session,
            opportunity_scan_id=scan_id,
            connection_id=self.context.connection.id,
            code=spec["code"],
            title=spec["title"],
            description=spec["description"],
            recommendation=spec["recommendation"],
            category=spec["category"],
            priority=spec["priority"],
            signal_codes_json=json.dumps(spec.get("signal_codes", []), default=str),
            roi_json=json.dumps(roi.model_dump(), default=str),
            evidence_json=json.dumps(spec.get("evidence", {}), default=str),
            status="recommended",
        )
        return BusinessOpportunityModel.model_validate(
            {
                "opportunity_id": row.id,
                "code": row.code,
                "title": row.title,
                "description": row.description,
                "recommendation": row.recommendation,
                "category": row.category,
                "priority": row.priority,
                "signal_codes": json.loads(row.signal_codes_json),
                "roi": roi.model_dump(),
                "evidence": json.loads(row.evidence_json),
                "card_label": f"{row.title} · ROI {roi.score}/100",
            }
        )

    def _build_roi_summary(self, opportunities: list[BusinessOpportunityModel]) -> dict[str, float | int | str]:
        if not opportunities:
            return {"total_score": 0, "average_score": 0, "highest_priority": 0, "top_opportunity": "none"}
        scores = [item.roi.score for item in opportunities]
        top = sorted(opportunities, key=lambda item: (item.priority, -item.roi.score))[0]
        return {
            "total_score": sum(scores),
            "average_score": round(sum(scores) / len(scores), 1),
            "highest_priority": min(item.priority for item in opportunities),
            "top_opportunity": top.title,
        }


class AutomationDraftBuilderService:
    def __init__(self, session) -> None:
        self.session = session

    def build(self, opportunity_id: str) -> AutomationDraftModel:
        opportunity_row = get_opportunity(self.session, opportunity_id)
        if opportunity_row is None:
            raise ObjectNotFoundError(f"Opportunity '{opportunity_id}' was not found.")

        scan_row = get_opportunity_scan(self.session, opportunity_row.opportunity_scan_id)
        if scan_row is None:
            raise ObjectNotFoundError(f"Opportunity scan '{opportunity_row.opportunity_scan_id}' was not found.")

        snapshot_row = get_business_snapshot(self.session, scan_row.business_snapshot_id)
        if snapshot_row is None:
            raise ObjectNotFoundError(f"Business snapshot '{scan_row.business_snapshot_id}' was not found.")

        draft_package = {
            "draft_kind": "non_executable_automation",
            "runtime_mode": "dry_run_only",
            "write_actions": False,
            "connection_id": snapshot_row.connection_id,
            "snapshot_id": snapshot_row.id,
            "scan_id": scan_row.id,
            "opportunity_id": opportunity_row.id,
            "opportunity_code": opportunity_row.code,
            "opportunity_title": opportunity_row.title,
            "steps": [
                {
                    "id": "review_evidence",
                    "type": "review",
                    "description": "Inspect the read-only business snapshot and the recommendation card.",
                },
                {
                    "id": "dry_run_plan",
                    "type": "plan",
                    "description": opportunity_row.recommendation,
                },
                {
                    "id": "no_write_execution",
                    "type": "guard",
                    "description": "Keep write_actions false and runtime_mode dry_run_only.",
                },
            ],
            "guards": ["read_only", "no_odoo_writes", "dry_run_only"],
        }
        row = create_automation_draft(
            self.session,
            opportunity_id=opportunity_row.id,
            scan_id=scan_row.id,
            snapshot_id=snapshot_row.id,
            connection_id=snapshot_row.connection_id,
            name=f"Draft - {opportunity_row.title}",
            description=opportunity_row.description,
            runtime_mode="dry_run_only",
            write_actions=False,
            draft_json=json.dumps(draft_package, default=str),
            status="created",
        )
        return AutomationDraftModel.model_validate(
            {
                "draft_id": row.id,
                "opportunity_id": row.opportunity_id,
                "scan_id": row.scan_id,
                "snapshot_id": row.snapshot_id,
                "connection_id": row.connection_id,
                "name": row.name,
                "description": row.description,
                "status": row.status,
                "runtime_mode": row.runtime_mode,
                "write_actions": row.write_actions,
                "draft_package": draft_package,
                "created_at": row.created_at.isoformat(),
            }
        )


class BusinessAnalysisService:
    def __init__(self, session, connection: Connection, config: OdooConfig) -> None:
        self.session = session
        self.connection = connection
        self.config = config
        self.context = ProductAnalysisContext(connection=connection, config=config)

    def analyze(self, request: BusinessAnalysisRequest) -> BusinessAnalysisResult:
        snapshot = BusinessSnapshotService(self.context, self.session).capture(request)
        signals = SignalService(self.context, self.session).derive(snapshot)
        scan, opportunities, roi_summary = OpportunityScannerService(self.context, self.session).scan(
            snapshot,
            signals,
            request.max_opportunities,
        )
        result = BusinessAnalysisResult.model_validate(
            {
                "connection_id": self.connection.id,
                "snapshot_id": snapshot.snapshot_id,
                "scan_id": scan.scan_id,
                "status": "ok",
                "read_only_mode": True,
                "snapshot": snapshot.model_dump(),
                "signals": [signal.model_dump() for signal in signals],
                "opportunities": [opportunity.model_dump() for opportunity in opportunities],
                "recommendation_cards": [opportunity.model_dump() for opportunity in opportunities],
                "roi_summary": roi_summary,
                "next_recommended_action": self._next_action(snapshot, opportunities),
                "secrets_redacted": True,
            }
        )
        create_audit_event(
            self.session,
            self.connection.id,
            "product_analysis_completed",
            {
                "event": "product_analysis_completed",
                "connection_id": self.connection.id,
                "snapshot_id": snapshot.snapshot_id,
                "scan_id": scan.scan_id,
                "opportunity_count": len(opportunities),
            },
        )
        return result

    def draft(self, opportunity_id: str) -> AutomationDraftModel:
        draft = AutomationDraftBuilderService(self.session).build(opportunity_id)
        create_audit_event(
            self.session,
            self.connection.id,
            "product_draft_created",
            {
                "event": "product_draft_created",
                "connection_id": self.connection.id,
                "draft_id": draft.draft_id,
                "opportunity_id": opportunity_id,
                "write_actions": False,
                "runtime_mode": "dry_run_only",
            },
        )
        return draft

    def _next_action(self, snapshot: BusinessSnapshotModel, opportunities: list[BusinessOpportunityModel]) -> str:
        if not opportunities:
            return "Review the snapshot and rerun the scan with more sample context."
        top = sorted(opportunities, key=lambda item: (item.priority, -item.roi.score))[0]
        return f"Review '{top.title}' and create a dry-run draft if it fits the roadmap."
