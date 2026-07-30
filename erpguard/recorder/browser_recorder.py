from __future__ import annotations

from dataclasses import dataclass, field
import json
from typing import Any
from urllib.parse import urljoin

from erpguard.db.repositories import add_recording_event, create_recording_session, finish_recording_session, list_recording_events
from erpguard.runtime.browser_runtime import BrowserRuntimeUnavailableError, is_playwright_browser_available


@dataclass(slots=True)
class BrowserRecordingStepResult:
    step_id: str
    event_type: str
    status: str
    url: str | None = None
    selector: str | None = None
    element_text: str | None = None
    before_text_snapshot: str | None = None
    after_text_snapshot: str | None = None
    error_text: str | None = None


@dataclass(slots=True)
class BrowserRecordingResult:
    recording_id: str
    status: str
    event_count: int
    order_reference: str
    visited_urls: list[str] = field(default_factory=list)
    selectors_used: list[str] = field(default_factory=list)
    no_llm_used: bool = True
    steps: list[BrowserRecordingStepResult] = field(default_factory=list)
    error_text: str | None = None


def record_fake_erp_formula_review_flow(base_url: str, order_reference: str, actor: dict[str, Any]) -> BrowserRecordingResult:
    if not is_playwright_browser_available():
        raise BrowserRuntimeUnavailableError("Playwright browser binaries are unavailable.")

    try:
        from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
        from playwright.sync_api import sync_playwright
    except Exception as exc:  # pragma: no cover - import guard
        raise BrowserRuntimeUnavailableError("Playwright is not installed.") from exc

    from erpguard.db.session import SessionLocal, init_db

    init_db()
    session = SessionLocal()
    visited_urls: list[str] = []
    selectors_used: list[str] = []
    steps: list[BrowserRecordingStepResult] = []

    def record_step(
        step_id: str,
        event_type: str,
        status: str,
        *,
        url: str | None = None,
        selector: str | None = None,
        element_text: str | None = None,
        before_text_snapshot: str | None = None,
        after_text_snapshot: str | None = None,
        error_text: str | None = None,
    ) -> None:
        steps.append(
            BrowserRecordingStepResult(
                step_id=step_id,
                event_type=event_type,
                status=status,
                url=url,
                selector=selector,
                element_text=element_text,
                before_text_snapshot=before_text_snapshot,
                after_text_snapshot=after_text_snapshot,
                error_text=error_text,
            )
        )
        if url and (not visited_urls or visited_urls[-1] != url):
            visited_urls.append(url)
        if selector:
            selectors_used.append(selector)

    recording = create_recording_session(
        session=session,
        name="Demo Fake ERP Formula Review",
        description="Automated demo recording of the Fake ERP formula review flow.",
        erp_type="fake",
        target_base_url=base_url,
        created_by_actor_json=json.dumps(actor, default=str),
    )

    try:
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(headless=True)
            page = browser.new_page()

            orders_url = urljoin(base_url.rstrip("/") + "/", "fake-erp/sales/orders")
            page.goto(orders_url, wait_until="domcontentloaded")
            body_before = ""
            body_after = page.locator("body").inner_text().strip()
            add_recording_event(
                session=session,
                recording_session_id=recording.id,
                event_type="navigate",
                url=page.url,
                page_title=page.title(),
                before_text_snapshot=body_before,
                after_text_snapshot=body_after,
                metadata_json=json.dumps({"source": "demo_recorder"}),
            )
            record_step("browser_open_orders", "navigate", "passed", url=page.url, before_text_snapshot=body_before, after_text_snapshot=body_after)

            search_selector = "[data-testid='order-search']"
            body_before = page.locator("body").inner_text().strip()
            page.locator(search_selector).fill(order_reference)
            body_after = page.locator("body").inner_text().strip()
            add_recording_event(
                session=session,
                recording_session_id=recording.id,
                event_type="fill",
                url=page.url,
                page_title=page.title(),
                element_role="searchbox",
                element_text=order_reference,
                selector=search_selector,
                input_value=order_reference,
                before_text_snapshot=body_before,
                after_text_snapshot=body_after,
                metadata_json=json.dumps({"source": "demo_recorder"}),
            )
            record_step(
                "browser_search_order",
                "fill",
                "passed",
                url=page.url,
                selector=search_selector,
                element_text=order_reference,
                before_text_snapshot=body_before,
                after_text_snapshot=body_after,
            )

            open_order_selector = f"[data-testid='open-order-{order_reference}']"
            body_before = page.locator("body").inner_text().strip()
            try:
                with page.expect_navigation(wait_until="domcontentloaded"):
                    page.locator(open_order_selector).click()
            except PlaywrightTimeoutError:
                page.locator(open_order_selector).click()
            body_after = page.locator("body").inner_text().strip()
            add_recording_event(
                session=session,
                recording_session_id=recording.id,
                event_type="click",
                url=page.url,
                page_title=page.title(),
                element_role="link",
                element_text=f"Open {order_reference}",
                selector=open_order_selector,
                before_text_snapshot=body_before,
                after_text_snapshot=body_after,
                metadata_json=json.dumps({"source": "demo_recorder"}),
            )
            record_step(
                "browser_open_order",
                "click",
                "passed",
                url=page.url,
                selector=open_order_selector,
                element_text=f"Open {order_reference}",
                before_text_snapshot=body_before,
                after_text_snapshot=body_after,
            )

            formula_selector = "[data-testid='formula-tab']"
            body_before = page.locator("body").inner_text().strip()
            try:
                with page.expect_navigation(wait_until="domcontentloaded"):
                    page.locator(formula_selector).click()
            except PlaywrightTimeoutError:
                page.locator(formula_selector).click()
            body_after = page.locator("body").inner_text().strip()
            add_recording_event(
                session=session,
                recording_session_id=recording.id,
                event_type="click",
                url=page.url,
                page_title=page.title(),
                element_role="link",
                element_text="Formula tab",
                selector=formula_selector,
                before_text_snapshot=body_before,
                after_text_snapshot=body_after,
                metadata_json=json.dumps({"source": "demo_recorder"}),
            )
            record_step(
                "browser_open_formula",
                "click",
                "passed",
                url=page.url,
                selector=formula_selector,
                element_text="Formula tab",
                before_text_snapshot=body_before,
                after_text_snapshot=body_after,
            )

            review_selector = "[data-testid='review-formula']"
            body_before = page.locator("body").inner_text().strip()
            page.locator(review_selector).click()
            body_after = page.locator("body").inner_text().strip()
            add_recording_event(
                session=session,
                recording_session_id=recording.id,
                event_type="click",
                url=page.url,
                page_title=page.title(),
                element_role="button",
                element_text="Review formula",
                selector=review_selector,
                before_text_snapshot=body_before,
                after_text_snapshot=body_after,
                metadata_json=json.dumps({"source": "demo_recorder"}),
            )
            record_step(
                "browser_review_formula",
                "click",
                "passed",
                url=page.url,
                selector=review_selector,
                element_text="Review formula",
                before_text_snapshot=body_before,
                after_text_snapshot=body_after,
            )

            finish_recording_session(session, recording.id, status="finished")
            browser.close()

        return BrowserRecordingResult(
            recording_id=recording.id,
            status="finished",
            event_count=len(list_recording_events(session, recording.id)),
            order_reference=order_reference,
            visited_urls=visited_urls,
            selectors_used=selectors_used,
            no_llm_used=True,
            steps=steps,
        )
    except Exception as exc:
        finish_recording_session(session, recording.id, status="failed")
        raise exc
    finally:
        session.close()
