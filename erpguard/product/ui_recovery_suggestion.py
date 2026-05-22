from __future__ import annotations

_SUGGESTIONS: dict[str, str] = {
    "wrong_target": (
        "Verify the target URL contains /fake-erp. "
        "Production ERP targets are not permitted for replay."
    ),
    "wrong_page": (
        "Navigate to the expected page before executing this step. "
        "The current page URL does not match the recorded page."
    ),
    "wrong_record": (
        "Verify the record reference matches a known Fake ERP order "
        "(SO-VALID, SO-FORMULA-MISMATCH, SO-CAPACITY-NO-FORMULA, SO-EMPTY-LINES). "
        "Re-record the flow if the target record has changed."
    ),
    "missing_selector": (
        "Re-record this step to capture a stable selector. "
        "The compiled skill references a selector that could not be located."
    ),
    "ambiguous_selector": (
        "Add a data-testid attribute to uniquely identify the target element. "
        "Text-based selectors are fragile and may match multiple elements."
    ),
    "unexpected_modal": (
        "Close the blocking error modal or resolve the validation warning "
        "before resuming replay. Do not use coordinate automation to dismiss it."
    ),
    "state_mismatch": (
        "Verify the ERP record state matches the state at recording time. "
        "The after-state did not match expectations — re-record if the record changed."
    ),
    "guard_finding": (
        "Review the guard finding and verify business data is as expected. "
        "This is informational and does not block execution."
    ),
    "no_failure": "No recovery action required — all verification checks passed.",
}


class UIRecoverySuggestionService:
    def suggest(self, failure_type: str, context: dict | None = None) -> str:
        base = _SUGGESTIONS.get(failure_type, f"Unknown failure type: {failure_type!r}.")
        if context and failure_type in ("wrong_page", "missing_selector"):
            step_id = context.get("step_id", "")
            if step_id:
                base = base + f" (Step: {step_id})"
        return base

    def all_suggestions(self) -> dict[str, str]:
        return dict(_SUGGESTIONS)
