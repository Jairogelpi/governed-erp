from __future__ import annotations

from dataclasses import dataclass


FAILURE_TYPES = frozenset({
    "wrong_target",
    "wrong_page",
    "wrong_record",
    "missing_selector",
    "ambiguous_selector",
    "unexpected_modal",
    "state_mismatch",
    "guard_finding",
    "no_failure",
})


@dataclass(frozen=True)
class FailureClassification:
    failure_type: str
    detail: str
    severity: str


class UIFailureClassifier:
    def classify(
        self,
        *,
        page_state_ok: bool,
        record_identity_ok: bool,
        selector_ambiguity_ok: bool,
        modal_error_ok: bool,
        post_state_ok: bool,
        page_detail: str = "",
        record_detail: str = "",
        selector_detail: str = "",
        modal_detail: str = "",
        post_detail: str = "",
    ) -> FailureClassification:
        if not page_state_ok:
            if "not_on_fake_erp" in page_detail or "wrong_target" in page_detail:
                return FailureClassification("wrong_target", page_detail, "critical")
            if "mismatch" in page_detail or "wrong_page" in page_detail:
                return FailureClassification("wrong_page", page_detail, "error")
            return FailureClassification("wrong_page", page_detail, "error")

        if not record_identity_ok:
            return FailureClassification("wrong_record", record_detail, "error")

        if not selector_ambiguity_ok:
            if "missing" in selector_detail:
                return FailureClassification("missing_selector", selector_detail, "error")
            if "ambiguous" in selector_detail or "text_based" in selector_detail:
                return FailureClassification("ambiguous_selector", selector_detail, "warning")
            return FailureClassification("missing_selector", selector_detail, "error")

        if not modal_error_ok:
            return FailureClassification("unexpected_modal", modal_detail, "error")

        if not post_state_ok:
            return FailureClassification("state_mismatch", post_detail, "warning")

        return FailureClassification("no_failure", "all_checks_passed", "none")
