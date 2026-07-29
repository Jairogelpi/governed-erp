from __future__ import annotations

from dataclasses import dataclass

_STABLE_SELECTORS = frozenset({
    "[data-testid='order-search']",
    "[data-testid='order-row-SO-VALID']",
    "[data-testid='order-row-SO-FORMULA-MISMATCH']",
    "[data-testid='order-row-SO-CAPACITY-NO-FORMULA']",
    "[data-testid='order-row-SO-EMPTY-LINES']",
    "[data-testid='open-order-SO-VALID']",
    "[data-testid='open-order-SO-FORMULA-MISMATCH']",
    "[data-testid='open-order-SO-CAPACITY-NO-FORMULA']",
    "[data-testid='open-order-SO-EMPTY-LINES']",
    "[data-testid='formula-tab']",
    "[data-testid='review-formula']",
    "[data-testid='formula-status']",
    "[data-testid='order-status-result']",
    "[data-testid='order-detail-title']",
    "[data-testid='order-customer']",
    "[data-testid='order-state']",
    "[data-testid='order-line-count']",
    "[aria-label='Formula tab']",
    "[aria-label='Review formula']",
    "[aria-label='Search orders']",
    "[name='q']",
    "[name='review-formula']",
})

_AMBIGUOUS_PATTERNS = ("button:text(", "a:text(", "element:text(", ":contains(")


@dataclass(frozen=True)
class SelectorAmbiguityResult:
    ok: bool
    check: str
    detail: str
    selector: str | None = None
    confidence: str = "high"


class UISelectorAmbiguityDetector:
    def detect(self, step: dict) -> SelectorAmbiguityResult:
        selector = step.get("selector")
        step_type = step.get("type", "")

        if step_type in ("navigate", "guard"):
            return SelectorAmbiguityResult(
                ok=True, check="selector_ambiguity",
                detail="step_type_does_not_require_selector",
            )

        if not selector:
            return SelectorAmbiguityResult(
                ok=False, check="selector_ambiguity",
                detail="missing_selector",
                selector=None, confidence="none",
            )

        if any(pattern in selector for pattern in _AMBIGUOUS_PATTERNS):
            return SelectorAmbiguityResult(
                ok=False, check="selector_ambiguity",
                detail="text_based_selector_is_ambiguous",
                selector=selector, confidence="low",
            )

        if "[data-testid=" in selector:
            in_stable = selector in _STABLE_SELECTORS
            return SelectorAmbiguityResult(
                ok=True, check="selector_ambiguity",
                detail="data_testid_selector_is_stable" if in_stable else "data_testid_selector_unrecognized",
                selector=selector, confidence="high",
            )

        if "[aria-label=" in selector or "[name=" in selector or "[placeholder=" in selector:
            return SelectorAmbiguityResult(
                ok=True, check="selector_ambiguity",
                detail="attribute_selector_acceptable",
                selector=selector, confidence="medium",
            )

        return SelectorAmbiguityResult(
            ok=True, check="selector_ambiguity",
            detail="selector_accepted",
            selector=selector, confidence="medium",
        )
