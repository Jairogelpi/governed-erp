"""Deterministic historical replay engine (master spec section 15).

No LLM or agent runtime is imported anywhere in this module -- replay must
never invoke one (spec 15.7). A case whose recorded canonical-object state
can't be turned into a `SalesOrder` returns `needs_clarification` instead of
guessing or crashing.

Connector writes are not simulated by a dedicated component here: replay
never calls a connector plugin at all, it only reads already-ingested
canonical events/objects and evaluates policy decisions against them. The
Fake connector plugin (which always returns `status="blocked"`) is the
system's existing simulation boundary for any live write path; replay simply
never enters that path, satisfying "no source ERP write" by construction.
"""

from __future__ import annotations

from pydantic import ValidationError

from erpguard.canonical.enums import CanonicalAction
from erpguard.canonical.objects import SalesOrder
from erpguard.domain.processes.candidate_integrity import stable_digest
from erpguard.domain.processes.models import ProcessDefinitionDocument
from erpguard.domain.variants.discovery import CaseTrace
from erpguard.domain.replays.types import (
    DecisionTrace,
    PredictedEffect,
    ReplayCaseResult,
    Violation,
)
from erpguard.policies.engine import evaluate_formula_guard_policy

CONNECTOR_SIMULATOR_VERSION = "fake-blocked-by-construction/1"

# Only decisions with a real evaluator are replayed; other declared decisions
# are skipped (not crashed on) -- see module docstring.
_DECISION_EVALUATORS = {"formula_guard"}


def _applicable_decisions(definition: ProcessDefinitionDocument, event_types: set[str]):
    return [
        decision
        for decision in definition.decisions
        if decision.applies_to in event_types and decision.name in _DECISION_EVALUATORS
    ]


class ReplayEngine:
    def run_case(
        self,
        *,
        process_key: str,
        version: str,
        object_type: str,
        case_trace: CaseTrace,
        definition: ProcessDefinitionDocument,
        object_attributes: dict,
    ) -> ReplayCaseResult:
        event_types = {event.event_type for event in case_trace.events}

        try:
            sales_order = SalesOrder.model_validate(object_attributes)
        except ValidationError as exc:
            error_fields = sorted({".".join(str(part) for part in err["loc"]) for err in exc.errors()})
            return ReplayCaseResult(
                case_id=case_trace.case_id,
                status="needs_clarification",
                deterministic_trace_hash=stable_digest(
                    {
                        "case_id": case_trace.case_id,
                        "process_key": process_key,
                        "version": version,
                        "object_type": object_type,
                        "status": "needs_clarification",
                        "reason": "recorded_state_insufficient_for_sales_order",
                        "invalid_fields": error_fields,
                    }
                ),
            )

        decision_trace: list[DecisionTrace] = []
        predicted_effects: list[PredictedEffect] = []
        safety_violations: list[Violation] = []
        status = "passed"

        for decision in _applicable_decisions(definition, event_types):
            result = evaluate_formula_guard_policy(sales_order, CanonicalAction.VALIDATE_FORMULA)
            outcome = "block" if result.issues else "allow"
            decision_trace.append(
                DecisionTrace(
                    decision_name=decision.name,
                    applies_to=decision.applies_to,
                    outcome=outcome,
                    policy_id=result.policy_id,
                    policy_version=result.policy_version,
                    summary=result.summary,
                    risk_level=result.risk_level.value,
                )
            )
            predicted_effects.append(
                PredictedEffect(
                    kind=f"{decision.name}.{outcome}",
                    description=result.summary,
                    evidence=result.evidence,
                )
            )
            if result.issues:
                status = "failed"
                for issue in result.issues:
                    safety_violations.append(
                        Violation(
                            code=issue.code,
                            message=issue.message,
                            evidence=issue.evidence,
                        )
                    )

        trace_hash = stable_digest(
            {
                "case_id": case_trace.case_id,
                "process_key": process_key,
                "version": version,
                "object_type": object_type,
                "status": status,
                "decision_trace": [item.model_dump(mode="json") for item in decision_trace],
            }
        )
        return ReplayCaseResult(
            case_id=case_trace.case_id,
            status=status,
            decision_trace=decision_trace,
            predicted_effects=predicted_effects,
            safety_violations=safety_violations,
            regressions=[],
            metrics={},
            deterministic_trace_hash=trace_hash,
        )
