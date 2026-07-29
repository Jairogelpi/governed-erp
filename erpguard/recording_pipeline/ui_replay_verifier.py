from __future__ import annotations

import json
from dataclasses import dataclass, field

from erpguard.recording_pipeline.ui_page_state_verifier import UIPageStateVerifier
from erpguard.recording_pipeline.ui_record_identity_verifier import UIRecordIdentityVerifier
from erpguard.recording_pipeline.ui_selector_ambiguity import UISelectorAmbiguityDetector
from erpguard.recording_pipeline.ui_modal_error_detector import UIModalErrorDetector
from erpguard.recording_pipeline.ui_failure_classifier import UIFailureClassifier, FailureClassification
from erpguard.recording_pipeline.ui_recovery_suggestion import UIRecoverySuggestionService


@dataclass(frozen=True)
class StepVerification:
    step_id: str
    step_index: int
    page_state_ok: bool
    record_identity_ok: bool
    selector_ambiguity_ok: bool
    modal_error_ok: bool
    post_state_ok: bool
    overall_status: str
    checks: dict = field(default_factory=dict)
    failure: FailureClassification | None = None
    recovery_suggestion: str = ""

    def all_pre_checks_ok(self) -> bool:
        return (
            self.page_state_ok
            and self.record_identity_ok
            and self.selector_ambiguity_ok
            and self.modal_error_ok
        )

    def to_checks_json(self) -> str:
        return json.dumps(self.checks, default=str)


class UIReplayVerifier:
    _page = UIPageStateVerifier()
    _record = UIRecordIdentityVerifier()
    _selector = UISelectorAmbiguityDetector()
    _modal = UIModalErrorDetector()
    _classifier = UIFailureClassifier()
    _suggest = UIRecoverySuggestionService()

    def verify_pre_step(self, step: dict, step_index: int, erp_state: dict) -> StepVerification:
        step_id = step.get("id", f"step_{step_index}")

        page_result = self._page.verify(step, erp_state)
        record_result = self._record.verify(step, erp_state)
        selector_result = self._selector.detect(step)
        modal_result = self._modal.detect(erp_state, step)

        classification = self._classifier.classify(
            page_state_ok=page_result.ok,
            record_identity_ok=record_result.ok,
            selector_ambiguity_ok=selector_result.ok,
            modal_error_ok=modal_result.ok,
            post_state_ok=True,
            page_detail=page_result.detail,
            record_detail=record_result.detail,
            selector_detail=selector_result.detail,
            modal_detail=modal_result.detail,
        )

        all_ok = page_result.ok and record_result.ok and selector_result.ok and modal_result.ok
        overall = "passed" if all_ok else "verification_failed"

        suggestion = ""
        if not all_ok:
            suggestion = self._suggest.suggest(
                classification.failure_type,
                context={"step_id": step_id},
            )

        checks = {
            "page_state": {"ok": page_result.ok, "detail": page_result.detail},
            "record_identity": {"ok": record_result.ok, "detail": record_result.detail},
            "selector_ambiguity": {"ok": selector_result.ok, "detail": selector_result.detail, "confidence": selector_result.confidence},
            "modal_error": {"ok": modal_result.ok, "detail": modal_result.detail, "blocking": getattr(modal_result, "blocking", False)},
        }

        return StepVerification(
            step_id=step_id,
            step_index=step_index,
            page_state_ok=page_result.ok,
            record_identity_ok=record_result.ok,
            selector_ambiguity_ok=selector_result.ok,
            modal_error_ok=modal_result.ok,
            post_state_ok=True,
            overall_status=overall,
            checks=checks,
            failure=classification if not all_ok else None,
            recovery_suggestion=suggestion,
        )

    def verify_post_step(
        self,
        verification: StepVerification,
        step: dict,
        before_state: dict,
        after_state: dict,
    ) -> StepVerification:
        step_type = step.get("type", "")
        post_ok = True
        post_detail = "post_state_not_checked"

        if step_type == "navigate":
            expected_url = step.get("url", "")
            actual_url = after_state.get("current_url", "")
            if expected_url and actual_url and expected_url != actual_url:
                path_exp = expected_url.split("/fake-erp", 1)[-1] if "/fake-erp" in expected_url else expected_url
                path_act = actual_url.split("/fake-erp", 1)[-1] if "/fake-erp" in actual_url else actual_url
                if path_exp and path_act and path_exp != path_act:
                    post_ok = False
                    post_detail = f"url_did_not_change_to_expected: {expected_url!r}"
            else:
                post_detail = "post_navigate_url_verified"

        elif step_type == "fill":
            order_before = before_state.get("current_order")
            order_after = after_state.get("current_order")
            if order_before is None and order_after is None:
                post_detail = "fill_did_not_set_order"
            else:
                post_detail = "fill_post_state_noted"

        else:
            post_detail = "post_state_accepted"

        if not post_ok and verification.overall_status == "passed":
            classification = self._classifier.classify(
                page_state_ok=True, record_identity_ok=True,
                selector_ambiguity_ok=True, modal_error_ok=True,
                post_state_ok=False, post_detail=post_detail,
            )
            suggestion = self._suggest.suggest(
                classification.failure_type, context={"step_id": verification.step_id}
            )
            updated_checks = dict(verification.checks)
            updated_checks["post_state"] = {"ok": False, "detail": post_detail}
            return StepVerification(
                step_id=verification.step_id,
                step_index=verification.step_index,
                page_state_ok=verification.page_state_ok,
                record_identity_ok=verification.record_identity_ok,
                selector_ambiguity_ok=verification.selector_ambiguity_ok,
                modal_error_ok=verification.modal_error_ok,
                post_state_ok=False,
                overall_status="verification_failed",
                checks=updated_checks,
                failure=classification,
                recovery_suggestion=suggestion,
            )

        updated_checks = dict(verification.checks)
        updated_checks["post_state"] = {"ok": post_ok, "detail": post_detail}
        return StepVerification(
            step_id=verification.step_id,
            step_index=verification.step_index,
            page_state_ok=verification.page_state_ok,
            record_identity_ok=verification.record_identity_ok,
            selector_ambiguity_ok=verification.selector_ambiguity_ok,
            modal_error_ok=verification.modal_error_ok,
            post_state_ok=post_ok,
            overall_status=verification.overall_status,
            checks=updated_checks,
            failure=verification.failure,
            recovery_suggestion=verification.recovery_suggestion,
        )
