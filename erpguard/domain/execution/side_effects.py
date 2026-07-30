"""Phase 17.1 confirmation side-effect contract.

The contract is descriptive and fail-closed.  It does not add a cancellation,
accounting or generic RPC capability.
"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from erpguard.domain.processes.candidate_integrity import stable_digest


class _StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class SideEffectBudget(_StrictModel):
    schema_version: Literal["erpguard.side_effect_budget.v1"] = "erpguard.side_effect_budget.v1"
    required_effects: list[str]
    allowed_effects: list[str]
    forbidden_effects: list[str]
    conditional_effects: dict[str, str] = Field(default_factory=dict)
    maximum_created_records: dict[str, int]


class AutomationFingerprint(_StrictModel):
    schema_version: Literal["erpguard.odoo_confirmation_fingerprint.v1"] = (
        "erpguard.odoo_confirmation_fingerprint.v1"
    )
    digest: str
    complete: bool
    server_version: str
    installed_modules: list[str]
    automated_action_count: int
    custom_sale_order_fields: list[str]
    model_access: dict[str, dict[str, bool]]
    configuration_signals: dict[str, Any] = Field(default_factory=dict)
    blocking_issues: list[str] = Field(default_factory=list)


class CompensationPlan(_StrictModel):
    schema_version: Literal["erpguard.compensation_plan.v1"] = "erpguard.compensation_plan.v1"
    mode: Literal["manual_governed_compensation"] = "manual_governed_compensation"
    automatic_rollback: Literal[False] = False
    trigger: str
    required_approval: str
    compensating_capabilities: list[str]
    affected_records: dict[str, list[int]] = Field(default_factory=dict)
    expected_neutral_effect: list[str]
    verification: list[str]
    residual_effects: list[str]
    operator_instructions: list[str]


class ConfirmationControlContract(_StrictModel):
    schema_version: Literal["erpguard.confirmation_control_contract.v1"] = (
        "erpguard.confirmation_control_contract.v1"
    )
    environment: str
    side_effect_budget: SideEffectBudget
    automation_fingerprint: AutomationFingerprint
    compensation_plan: CompensationPlan

    @property
    def digest(self) -> str:
        return stable_digest(self.model_dump(mode="json"))


class SideEffectObservation(_StrictModel):
    effect: str
    model: str | None = None
    record_ids: list[int] = Field(default_factory=list)
    count: int = 0
    detail: str = ""


class SideEffectEvaluation(_StrictModel):
    status: Literal["within_budget", "budget_exceeded"]
    observations: list[SideEffectObservation]
    violations: list[str]
    created_records: dict[str, list[int]]

    @property
    def verified(self) -> bool:
        return self.status == "within_budget"


_SNAPSHOT_COLLECTIONS = {
    "stock.picking": "pickings",
    "account.move": "invoices",
    "account.payment": "payments",
    "purchase.order": "purchase_orders",
    "mrp.production": "manufacturing_orders",
}

_CREATION_EFFECTS = {
    "stock.picking": "stock_picking_creation",
    "account.move": "invoice_creation",
    "account.payment": "payment_creation",
    "purchase.order": "purchase_order_creation",
    "mrp.production": "manufacturing_order_creation",
}


def default_confirmation_budget() -> SideEffectBudget:
    return SideEffectBudget(
        required_effects=["sale_order_confirmation"],
        allowed_effects=["stock_picking_creation", "stock_reservation"],
        forbidden_effects=[
            "stock_picking_completion",
            "invoice_creation",
            "invoice_posting",
            "payment_creation",
            "purchase_order_creation",
            "manufacturing_order_creation",
        ],
        conditional_effects={
            "stock_picking_creation": "created count must not exceed ceiling and no picking may be done",
            "stock_reservation": "allowed only on a generated uncompleted picking",
        },
        maximum_created_records={
            "stock.picking": 1,
            "account.move": 0,
            "account.payment": 0,
            "purchase.order": 0,
            "mrp.production": 0,
        },
    )


def default_compensation_plan(order_id: int | None) -> CompensationPlan:
    affected = {"sale.order": [order_id]} if order_id is not None else {}
    return CompensationPlan(
        trigger="postcondition_failed_after_confirmation",
        required_approval="separate_explicit_operator_approval",
        compensating_capabilities=[
            "stock.picking.cancel_uncompleted",
            "account.move.reverse_posted_invoice",
            "sale.order.cancel",
        ],
        affected_records=affected,
        expected_neutral_effect=[
            "no completed delivery",
            "invoice and linked credit note residuals equal zero",
            "net documentary total equals zero",
            "sale order is cancelled",
        ],
        verification=[
            "re-read every affected record after each compensating step",
            "verify credit note is linked to the original invoice",
            "verify accounting documents remain preserved",
        ],
        residual_effects=[
            "the original invoice remains posted and auditable",
            "the reversing credit note remains posted and auditable",
            "audit and Evidence Pack records are never deleted",
        ],
        operator_instructions=[
            "stop if any picking is done or any payment exists",
            "cancel only uncompleted logistics first",
            "reverse a posted invoice with a linked credit note; never delete it",
            "cancel the order only after downstream compensation is verified",
        ],
    )


def fingerprint_from_evidence(evidence: dict[str, Any]) -> AutomationFingerprint:
    canonical = {
        "server_version": str(evidence.get("server_version") or "unknown"),
        "installed_modules": sorted(str(item) for item in evidence.get("installed_modules", [])),
        "automated_action_count": int(evidence.get("automated_action_count") or 0),
        "custom_sale_order_fields": sorted(
            str(item) for item in evidence.get("custom_sale_order_fields", [])
        ),
        "model_access": evidence.get("model_access", {}),
        "configuration_signals": evidence.get("configuration_signals", {}),
        "blocking_issues": sorted(str(item) for item in evidence.get("blocking_issues", [])),
    }
    return AutomationFingerprint(
        digest=stable_digest(canonical),
        complete=not canonical["blocking_issues"],
        **canonical,
    )


def _ids(snapshot: dict[str, Any], collection: str) -> set[int]:
    return {
        int(item["id"])
        for item in snapshot.get(collection, [])
        if isinstance(item, dict) and item.get("id") is not None
    }


def evaluate_confirmation_effects(
    before: dict[str, Any],
    after: dict[str, Any],
    budget: SideEffectBudget,
) -> SideEffectEvaluation:
    observations: list[SideEffectObservation] = []
    violations: list[str] = []
    created_records: dict[str, list[int]] = {}

    confirmed = after.get("state") in {"sale", "done"}
    observations.append(
        SideEffectObservation(
            effect="sale_order_confirmation",
            model="sale.order",
            record_ids=[int(after["order_id"])] if after.get("order_id") is not None else [],
            count=1 if confirmed else 0,
            detail=f"{before.get('state')}->{after.get('state')}",
        )
    )
    if "sale_order_confirmation" in budget.required_effects and not confirmed:
        violations.append(f"required_effect_missing:sale_order_confirmation:{after.get('state')}")

    for model, collection in _SNAPSHOT_COLLECTIONS.items():
        created = sorted(_ids(after, collection) - _ids(before, collection))
        created_records[model] = created
        effect = _CREATION_EFFECTS[model]
        if created:
            observations.append(
                SideEffectObservation(
                    effect=effect,
                    model=model,
                    record_ids=created,
                    count=len(created),
                )
            )
        maximum = budget.maximum_created_records.get(model)
        if maximum is not None and len(created) > maximum:
            violations.append(f"created_record_budget_exceeded:{model}:{len(created)}>{maximum}")
        if created and effect in budget.forbidden_effects:
            violations.append(f"forbidden_effect_observed:{effect}")

    created_picking_ids = set(created_records.get("stock.picking", []))
    completed_picking_ids = sorted(
        int(item["id"])
        for item in after.get("pickings", [])
        if isinstance(item, dict)
        and item.get("id") is not None
        and int(item["id"]) in created_picking_ids
        and item.get("state") == "done"
    )
    if completed_picking_ids:
        observations.append(
            SideEffectObservation(
                effect="stock_picking_completion",
                model="stock.picking",
                record_ids=completed_picking_ids,
                count=len(completed_picking_ids),
            )
        )
        violations.append("forbidden_effect_observed:stock_picking_completion")

    before_invoices = {
        int(item["id"]): item
        for item in before.get("invoices", [])
        if isinstance(item, dict) and item.get("id") is not None
    }
    posted_ids = sorted(
        int(item["id"])
        for item in after.get("invoices", [])
        if isinstance(item, dict)
        and item.get("id") is not None
        and item.get("state") == "posted"
        and before_invoices.get(int(item["id"]), {}).get("state") != "posted"
    )
    if posted_ids:
        observations.append(
            SideEffectObservation(
                effect="invoice_posting",
                model="account.move",
                record_ids=posted_ids,
                count=len(posted_ids),
            )
        )
        if "invoice_posting" in budget.forbidden_effects:
            violations.append("forbidden_effect_observed:invoice_posting")

    return SideEffectEvaluation(
        status="budget_exceeded" if violations else "within_budget",
        observations=observations,
        violations=sorted(set(violations)),
        created_records=created_records,
    )


def materialize_compensation_plan(
    template: CompensationPlan,
    evaluation: SideEffectEvaluation,
    order_id: int | None,
) -> CompensationPlan:
    affected = {
        model: ids
        for model, ids in evaluation.created_records.items()
        if ids
    }
    if order_id is not None:
        affected["sale.order"] = [order_id]
    return template.model_copy(update={"affected_records": affected})
