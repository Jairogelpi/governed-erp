from __future__ import annotations

from dataclasses import dataclass

_KNOWN_ORDERS = frozenset({
    "SO-VALID",
    "SO-FORMULA-MISMATCH",
    "SO-CAPACITY-NO-FORMULA",
    "SO-EMPTY-LINES",
})

_RECORD_REQUIRED_STEP_TYPES = frozenset({"guard"})
_RECORD_HELPFUL_STEP_TYPES = frozenset({"click"})


@dataclass(frozen=True)
class RecordIdentityResult:
    ok: bool
    check: str
    detail: str
    record_ref: str | None = None


class UIRecordIdentityVerifier:
    def verify(self, step: dict, erp_state: dict) -> RecordIdentityResult:
        step_type = step.get("type", "")

        if step_type not in _RECORD_REQUIRED_STEP_TYPES and step_type not in _RECORD_HELPFUL_STEP_TYPES:
            return RecordIdentityResult(ok=True, check="record_identity", detail="step_does_not_require_record")

        current_order = erp_state.get("current_order")

        if step_type in _RECORD_REQUIRED_STEP_TYPES:
            if not current_order:
                return RecordIdentityResult(
                    ok=False, check="record_identity",
                    detail="no_order_in_erp_state_for_guard_step",
                )
            if current_order not in _KNOWN_ORDERS:
                return RecordIdentityResult(
                    ok=False, check="record_identity",
                    detail="unknown_order_reference",
                    record_ref=current_order,
                )

        if current_order and current_order not in _KNOWN_ORDERS:
            return RecordIdentityResult(
                ok=False, check="record_identity",
                detail="unknown_order_reference",
                record_ref=current_order,
            )

        return RecordIdentityResult(
            ok=True, check="record_identity",
            detail="record_identity_verified",
            record_ref=current_order,
        )
