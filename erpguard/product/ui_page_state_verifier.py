from __future__ import annotations

from dataclasses import dataclass

_FAKE_ERP_MARKER = "/fake-erp"


@dataclass(frozen=True)
class PageStateResult:
    ok: bool
    check: str
    detail: str
    expected: str | None = None
    actual: str | None = None


class UIPageStateVerifier:
    def verify(self, step: dict, erp_state: dict) -> PageStateResult:
        step_type = step.get("type", "")
        current_url = erp_state.get("current_url", "")

        if step_type == "navigate":
            return PageStateResult(ok=True, check="page_state", detail="navigate_step_always_valid")

        if not current_url:
            return PageStateResult(
                ok=False, check="page_state",
                detail="no_current_url_in_erp_state",
                expected=_FAKE_ERP_MARKER, actual=None,
            )

        if _FAKE_ERP_MARKER not in current_url:
            return PageStateResult(
                ok=False, check="page_state",
                detail="current_url_not_on_fake_erp",
                expected=_FAKE_ERP_MARKER, actual=current_url,
            )

        expected_url = step.get("url")
        if expected_url and expected_url != current_url:
            path_expected = expected_url.split("/fake-erp", 1)[-1] if "/fake-erp" in expected_url else expected_url
            path_actual = current_url.split("/fake-erp", 1)[-1] if "/fake-erp" in current_url else current_url
            if path_expected and path_actual and path_expected != path_actual:
                return PageStateResult(
                    ok=False, check="page_state",
                    detail="page_url_mismatch",
                    expected=expected_url, actual=current_url,
                )

        return PageStateResult(ok=True, check="page_state", detail="page_state_verified", actual=current_url)
