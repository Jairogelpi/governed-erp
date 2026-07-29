from __future__ import annotations

from dataclasses import dataclass

_BLOCKING_ORDER_STATES = {
    "SO-EMPTY-LINES": "order_has_no_lines",
}


@dataclass(frozen=True)
class ModalErrorResult:
    ok: bool
    check: str
    detail: str
    blocking: bool = False
    modal_type: str | None = None


class UIModalErrorDetector:
    def detect(self, erp_state: dict, step: dict) -> ModalErrorResult:
        step_type = step.get("type", "")
        current_order = erp_state.get("current_order")

        if step_type == "navigate":
            return ModalErrorResult(ok=True, check="modal_error", detail="navigate_step_no_modal_check")

        error_state = erp_state.get("error_state")
        if error_state:
            return ModalErrorResult(
                ok=False, check="modal_error",
                detail=f"explicit_error_state_detected: {error_state}",
                blocking=True, modal_type="error",
            )

        if current_order and step_type == "guard":
            blocking_reason = _BLOCKING_ORDER_STATES.get(current_order)
            if blocking_reason:
                return ModalErrorResult(
                    ok=False, check="modal_error",
                    detail=f"order_state_blocks_guard: {blocking_reason}",
                    blocking=True, modal_type="validation_warning",
                )

        last_click = erp_state.get("last_click", "")
        if last_click and "error" in last_click.lower():
            return ModalErrorResult(
                ok=False, check="modal_error",
                detail=f"last_click_suggests_error_context: {last_click}",
                blocking=True, modal_type="error",
            )

        return ModalErrorResult(ok=True, check="modal_error", detail="no_blocking_modal_detected")
