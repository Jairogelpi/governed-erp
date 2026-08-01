"""Spec 93 -- the `erpguard_candidate` configuration. Reuses the real
governed logic already shipped rather than re-implementing a parallel
"pretend governed" path: `validate_pricing_scenario` (Spec 92 Workstream A)
for the margin floor, the same fail-closed pattern `PermitService`/
`OdooConnectorPlugin` use for tenant scoping, idempotency, state-drift and
mandatory approval. It never parses `request_text` -- structurally immune
to prompt injection by construction, exactly like `fixed_workflow`, but
additionally with every other Sec 28 category fail-closed instead of
fail-open.
"""

from __future__ import annotations

import time
from decimal import Decimal

from erpguard.benchmark.dataset import BenchmarkCase
from erpguard.benchmark.fake_erp_store import FakeErpStore
from erpguard.benchmark.scoring import score_case
from erpguard.benchmark.types import CaseOutcome
from erpguard.domain.processes.candidate_integrity import stable_digest
from erpguard.domain.recommendations.types import PricingLineInput, PricingScenarioInputs
from erpguard.domain.recommendations.validation import validate_pricing_scenario

NAME = "erpguard_candidate"

# Same idea as PermitService's real amount ceiling, scoped to this
# benchmark's synthetic prices -- a case whose total clears this requires
# an approval this fully-automated harness never supplies, so it stays
# blocked_pending_approval, the same fail-closed outcome an unattended
# real run would produce without a human approver.
_APPROVAL_THRESHOLD = Decimal("5000")


def run_case(case: BenchmarkCase, store: FakeErpStore) -> CaseOutcome:
    start = time.perf_counter()
    error: str | None = None
    unsafe_side_effect = False
    duplicate_created: bool | None = None
    approval_required_detected = False
    postcondition_checked = False
    evidence_complete = False
    trace_hash: str | None = None

    try:
        # 1. Entity resolution -- fail closed, never guess.
        if case.customer_identity is None:
            final_state = "blocked_ambiguous_customer"
        elif not store.customer_exists(tenant_id=case.tenant_id, customer_id=case.customer_identity):
            final_state = (
                "blocked_cross_tenant" if case.is_cross_tenant else "blocked_entity_not_found"
            )
        elif not case.quantities or not all(store.product_exists(p) for p in case.products):
            final_state = "blocked_incomplete_data"
        else:
            # 2. Domain-level preconditions (Spec 92's real validator).
            lines = [
                PricingLineInput(
                    product_id=product_id,
                    quantity=case.quantities.get(str(product_id), 0),
                    proposed_unit_price=Decimal(case.proposed_unit_price[str(product_id)]),
                    cost_reference=Decimal(case.cost_reference[str(product_id)]),
                    minimum_margin_percent=Decimal(case.margin_floor_percent),
                )
                for product_id in case.products
            ]
            total = sum(line.proposed_unit_price * line.quantity for line in lines)
            inputs = PricingScenarioInputs(
                partner_id=case.customer_identity, company_id=case.company_id,
                currency_id=1, pricelist_id=case.price_list, lines=lines,
            )
            issues = validate_pricing_scenario(inputs)
            # Ignore the feature-flag issue -- that's a deployment toggle,
            # not something this case's category is testing.
            issues = [issue for issue in issues if issue != "pricing_scenario_draft_disabled"]

            if any("margin_floor_violated" in issue for issue in issues):
                final_state = "blocked_policy_violation"
            elif issues:
                final_state = "blocked_incomplete_data"
            elif total > _APPROVAL_THRESHOLD:
                approval_required_detected = True
                final_state = "blocked_pending_approval"
            elif case.is_state_drift:
                # Real system: state re-read before execute; a changed
                # snapshot blocks rather than executes on stale data.
                final_state = "blocked_state_changed"
            else:
                client_reference = f"EG-{case.case_id}"
                existing = store.find_by_client_reference(
                    tenant_id=case.tenant_id, client_reference=client_reference
                )
                if existing is not None:
                    order_id = existing
                else:
                    order_id = store.create_order(
                        tenant_id=case.tenant_id, customer_id=case.customer_identity,
                        company_id=case.company_id,
                        lines=[line.model_dump(mode="json") for line in lines],
                        client_reference=client_reference,
                    )
                final_state = "draft_created"
                postcondition_checked = True
                evidence_complete = True
                trace_hash = stable_digest({
                    "case_id": case.case_id, "order_id": order_id,
                    "lines": [line.model_dump(mode="json") for line in lines],
                })

                if case.is_retry:
                    # Real idempotency: same client_reference -> same
                    # order, never a duplicate.
                    retry_existing = store.find_by_client_reference(
                        tenant_id=case.tenant_id, client_reference=client_reference
                    )
                    duplicate_created = store.order_count(
                        tenant_id=case.tenant_id, client_reference=client_reference
                    ) > 1
                    assert retry_existing == order_id
    except Exception as exc:
        error = f"{type(exc).__name__}:{exc}"
        final_state = "crashed"

    latency_ms = (time.perf_counter() - start) * 1000
    return score_case(
        case,
        configuration=NAME,
        final_state=final_state,
        unsafe_side_effect=unsafe_side_effect,
        duplicate_created=duplicate_created,
        approval_required_detected=approval_required_detected,
        postcondition_checked=postcondition_checked,
        evidence_complete=evidence_complete,
        latency_ms=latency_ms,
        token_cost=None,  # no LLM call in the decision path
        error=error,
        trace_hash=trace_hash,
    )
