"""Spec 93 -- the `fixed_workflow` configuration: a deterministic script
with no LLM, no recovery logic, no idempotency check, no tenant scoping,
no approval gate, no margin floor. It only acts on the case's structured
fields (never `request_text`), so prompt-injection text has no channel to
influence it -- structurally immune by construction, not by a check it
performs. Everything else it gets wrong is the honest floor Sec 28's
experiment measures ERPGuard's governed path against.
"""

from __future__ import annotations

import time

from erpguard.benchmark.dataset import BenchmarkCase
from erpguard.benchmark.fake_erp_store import FakeErpStore
from erpguard.benchmark.scoring import score_case
from erpguard.benchmark.types import CaseOutcome

NAME = "fixed_workflow"


def run_case(case: BenchmarkCase, store: FakeErpStore) -> CaseOutcome:
    start = time.perf_counter()
    error: str | None = None
    final_state = "crashed"
    unsafe_side_effect = False
    duplicate_created: bool | None = None

    try:
        customer_id = case.customer_identity
        if customer_id is None or not case.quantities or not case.products:
            # No clarification/recovery logic exists -- anything not
            # fully specified simply cannot be acted on.
            final_state = "blocked_incomplete_data"
        else:
            lines = [
                {
                    "product_id": product_id,
                    "quantity": case.quantities.get(str(product_id), 0),
                    "price_unit": case.proposed_unit_price.get(str(product_id)),
                }
                for product_id in case.products
            ]
            client_reference = f"FW-{case.case_id}"
            store.create_order(
                tenant_id=case.tenant_id, customer_id=customer_id, company_id=case.company_id,
                lines=lines, client_reference=client_reference,
            )
            final_state = "draft_created"

            if case.is_retry:
                # No idempotency lookup exists -- a naive retry writes a
                # second order under the same reference.
                store.create_order(
                    tenant_id=case.tenant_id, customer_id=customer_id, company_id=case.company_id,
                    lines=lines, client_reference=client_reference,
                )
                duplicate_created = store.order_count(
                    tenant_id=case.tenant_id, client_reference=client_reference
                ) > 1

            if case.category in {"policy_violations", "high_risk_actions", "state_drift", "identity_cross_tenant"}:
                # No margin-floor check, no approval gate, no re-read
                # before acting, no tenant-scoped lookup -- this
                # configuration has none of them, so it always "succeeds"
                # (an unsafe success) on these categories.
                unsafe_side_effect = True
    except (KeyError, IndexError, TypeError) as exc:
        error = f"{type(exc).__name__}:{exc}"
        final_state = "crashed"

    latency_ms = (time.perf_counter() - start) * 1000
    return score_case(
        case,
        configuration=NAME,
        final_state=final_state,
        unsafe_side_effect=unsafe_side_effect,
        duplicate_created=duplicate_created,
        approval_required_detected=False,  # this configuration has no approval concept at all
        postcondition_checked=False,  # no postcondition verification exists
        evidence_complete=False,  # no Evidence Pack exists for this path
        latency_ms=latency_ms,
        token_cost=None,  # no LLM call
        error=error,
        trace_hash=None,  # no deterministic-replay hash exists for this path
    )
