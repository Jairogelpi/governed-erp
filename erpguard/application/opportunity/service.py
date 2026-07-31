"""Phase 16.6 Opportunity & ROI engine: MarginAnalysis -> MarginOpportunity.

Turns a *reliable* `MarginAnalysis` (Phase 16.5) into evaluable
`MarginOpportunity` rows via deterministic rules
(`erpguard/domain/opportunity/rules.py`), not a forecasting model. A
blocked `MarginAnalysis` yields no opportunities -- silently returning an
empty list would look identical to "nothing found", so callers get an
explicit `blocked` flag instead. Scenario spread (conservative/optimistic)
is a fixed, documented haircut/uplift on the rule-derived base impact, not
a tuned forecast -- this is intentionally simple v1.
"""

from __future__ import annotations

import json
from decimal import Decimal
from uuid import uuid4

from sqlalchemy.orm import Session

from erpguard.db.model_packages.decision_intelligence import DataQualityReport, MarginAnalysis
from erpguard.db.model_packages.opportunity import MarginOpportunity
from erpguard.domain.opportunity.rules import detect_opportunities
from erpguard.domain.processes.candidate_integrity import stable_digest

CONSERVATIVE_FACTOR = Decimal("0.6")
OPTIMISTIC_FACTOR = Decimal("1.3")

_CONFIDENCE_BAND_BY_GRADE = {"A": "high", "B": "medium", "C": "low"}


class OpportunityNotFound(KeyError):
    pass


def _dump(value) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"))


def _risk_level(cost_coverage_rate: float) -> str:
    if cost_coverage_rate >= 0.95:
        return "low"
    if cost_coverage_rate >= 0.8:
        return "medium"
    return "high"


class OpportunityEngineService:
    def __init__(self, session: Session):
        self.session = session

    def generate(self, *, tenant_id: str, margin_analysis_id: str, created_by: str) -> list[MarginOpportunity]:
        existing = (
            self.session.query(MarginOpportunity)
            .filter_by(tenant_id=tenant_id, margin_analysis_id=margin_analysis_id)
            .order_by(MarginOpportunity.created_at.asc(), MarginOpportunity.id.asc())
            .all()
        )
        if existing:
            return existing

        analysis = (
            self.session.query(MarginAnalysis)
            .filter_by(tenant_id=tenant_id, id=margin_analysis_id)
            .one_or_none()
        )
        if analysis is None:
            raise OpportunityNotFound("margin_analysis_not_found")
        if analysis.status == "blocked":
            return []

        report = (
            self.session.query(DataQualityReport)
            .filter_by(tenant_id=tenant_id, snapshot_id=analysis.snapshot_id)
            .one()
        )
        confidence_band = _CONFIDENCE_BAND_BY_GRADE.get(report.confidence_grade, "low")
        risk_level = _risk_level(report.cost_coverage_rate)

        product_drivers = json.loads(analysis.product_drivers_json)
        customer_drivers = json.loads(analysis.customer_drivers_json)
        results = detect_opportunities(product_drivers=product_drivers, customer_drivers=customer_drivers)

        rows: list[MarginOpportunity] = []
        for result in results:
            base = result.impact_base
            conservative = base * CONSERVATIVE_FACTOR
            optimistic = base * OPTIMISTIC_FACTOR
            evidence_payload = [item.model_dump(mode="json") for item in result.evidence]
            content = {
                "margin_analysis_content_hash": analysis.content_hash,
                "cause": result.cause,
                "affected_population": result.affected_population,
                "evidence": evidence_payload,
                "impact_base": str(base),
            }
            row = MarginOpportunity(
                id=f"opp_{uuid4().hex}",
                tenant_id=tenant_id,
                margin_analysis_id=analysis.id,
                snapshot_id=analysis.snapshot_id,
                cause=result.cause,
                affected_population_json=_dump(result.affected_population),
                evidence_json=_dump(evidence_payload),
                impact_conservative=str(conservative),
                impact_base=str(base),
                impact_optimistic=str(optimistic),
                confidence_band=confidence_band,
                risk_level=risk_level,
                implementation_cost=None,
                payback_period_days=None,
                proposed_action=result.proposed_action,
                status="proposed",
                content_hash=stable_digest(content),
                created_by=created_by,
            )
            self.session.add(row)
            rows.append(row)

        self.session.commit()
        for row in rows:
            self.session.refresh(row)
        return rows

    def list_opportunities(self, *, tenant_id: str, margin_analysis_id: str) -> list[MarginOpportunity]:
        return (
            self.session.query(MarginOpportunity)
            .filter_by(tenant_id=tenant_id, margin_analysis_id=margin_analysis_id)
            .order_by(MarginOpportunity.created_at.asc(), MarginOpportunity.id.asc())
            .all()
        )
