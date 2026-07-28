from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any
from urllib.parse import urljoin

from erpguard.canonical.enums import CanonicalAction, PreflightDecision, SalesOrderState, ProductTracking, ProductType
from erpguard.canonical.objects import Company, Customer, FormulaLine, Product, SalesOrder, SalesOrderLine
from erpguard.core.errors import ObjectNotFoundError
from erpguard.policies.engine import PolicyEngine


@dataclass(slots=True)
class BrowserSkillRunStepResult:
    step_id: str
    step_type: str
    status: str
    url: str | None = None
    selector: str | None = None
    input_json: dict[str, Any] | None = None
    output_json: dict[str, Any] | None = None
    error_text: str | None = None


@dataclass(slots=True)
class BrowserSkillRunResult:
    status: str
    decision: str
    output: dict[str, Any]
    issues: list[dict[str, Any]]
    steps: list[BrowserSkillRunStepResult] = field(default_factory=list)
    visited_urls: list[str] = field(default_factory=list)
    selectors_used: list[str] = field(default_factory=list)
    token_economics: dict[str, int] = field(default_factory=dict)
    no_llm_used: bool = True
    error_text: str | None = None


class BrowserRuntimeUnavailableError(RuntimeError):
    pass


def is_playwright_browser_available() -> bool:
    try:
        from playwright.sync_api import sync_playwright  # type: ignore[import-not-found]
    except Exception:
        return False

    try:
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(headless=True)
            browser.close()
        return True
    except Exception:
        return False


def run_fake_erp_formula_skill_ui(base_url: str, order_reference: str) -> BrowserSkillRunResult:
    try:
        from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
        from playwright.sync_api import sync_playwright
    except Exception as exc:  # pragma: no cover - import guard
        raise BrowserRuntimeUnavailableError("Playwright is not installed.") from exc

    base_url = base_url.rstrip("/")
    orders_url = urljoin(base_url + "/", "fake-erp/sales/orders")
    urljoin(base_url + "/", f"fake-erp/sales/orders/{order_reference}")
    formula_url = urljoin(base_url + "/", f"fake-erp/sales/orders/{order_reference}/formula")
    selectors_used: list[str] = []
    visited_urls: list[str] = []
    steps: list[BrowserSkillRunStepResult] = []

    def record_step(
        step_id: str,
        step_type: str,
        status: str,
        *,
        url: str | None = None,
        selector: str | None = None,
        input_json: dict[str, Any] | None = None,
        output_json: dict[str, Any] | None = None,
        error_text: str | None = None,
    ) -> None:
        steps.append(
            BrowserSkillRunStepResult(
                step_id=step_id,
                step_type=step_type,
                status=status,
                url=url,
                selector=selector,
                input_json=input_json,
                output_json=output_json,
                error_text=error_text,
            )
        )
        if url and (not visited_urls or visited_urls[-1] != url):
            visited_urls.append(url)
        if selector:
            selectors_used.append(selector)

    try:
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(headless=True)
            page = browser.new_page()

            page.goto(orders_url, wait_until="domcontentloaded")
            record_step("browser_open_orders", "navigate", "passed", url=page.url, output_json={"title": page.title()})

            search_selector = "[data-testid='order-search']"
            page.locator(search_selector).fill(order_reference)
            record_step(
                "browser_search_order",
                "fill",
                "passed",
                url=page.url,
                selector=search_selector,
                input_json={"order_reference": order_reference},
            )

            open_order_selector = f"[data-testid='open-order-{order_reference}']"
            open_order = page.locator(open_order_selector)
            if open_order.count() == 0:
                record_step(
                    "browser_open_order",
                    "click",
                    "failed",
                    url=page.url,
                    selector=open_order_selector,
                    error_text=f"Order '{order_reference}' not found in Fake ERP Web.",
                )
                browser.close()
                return _failed_result(
                    order_reference=order_reference,
                    status="failed",
                    decision="block",
                    error_text=f"Order '{order_reference}' not found in Fake ERP Web.",
                    steps=steps,
                    visited_urls=visited_urls,
                    selectors_used=selectors_used,
                )

            try:
                with page.expect_navigation(wait_until="domcontentloaded"):
                    open_order.click()
            except PlaywrightTimeoutError:
                open_order.click()
            record_step("browser_open_order", "click", "passed", url=page.url, selector=open_order_selector)

            formula_selector = "[data-testid='formula-tab']"
            try:
                with page.expect_navigation(wait_until="domcontentloaded"):
                    page.locator(formula_selector).click()
            except PlaywrightTimeoutError:
                page.locator(formula_selector).click()
            record_step("browser_open_formula", "click", "passed", url=page.url, selector=formula_selector)

            if page.url != formula_url:
                page.goto(formula_url, wait_until="domcontentloaded")
                record_step("browser_open_formula", "navigate", "passed", url=page.url)

            review_selector = "[data-testid='review-formula']"
            page.locator(review_selector).click()
            record_step("browser_review_formula", "click", "passed", url=page.url, selector=review_selector)

            formula_values = _extract_formula_values(page)
            detail_values = _extract_detail_values(page)
            order = _build_sales_order(order_reference, detail_values, formula_values)

            record_step(
                "browser_extract_formula",
                "extract",
                "passed",
                url=page.url,
                output_json={"formula_values": formula_values, "detail_values": detail_values},
            )

            policy_result = PolicyEngine().evaluate("formula_guard", order, canonical_action=CanonicalAction.VALIDATE_FORMULA)
            record_step(
                "formula_guard",
                "guard",
                "blocked" if policy_result.decision is PreflightDecision.BLOCK else "passed",
                url=page.url,
                output_json=policy_result.model_dump(mode="json"),
            )

            output = {
                "order_reference": order.reference,
                "policy_id": policy_result.policy_id,
                "policy_version": policy_result.policy_version,
                "issues": [issue.model_dump(mode="json") for issue in policy_result.issues],
            }
            record_step(
                "produce_result",
                "result",
                "passed",
                url=page.url,
                output_json={"decision": policy_result.decision.value, "issues_count": len(policy_result.issues)},
            )
            browser.close()
            return BrowserSkillRunResult(
                status="success" if policy_result.decision is not PreflightDecision.BLOCK else "success",
                decision=policy_result.decision.value,
                output=output,
                issues=[issue.model_dump(mode="json") for issue in policy_result.issues],
                steps=steps,
                visited_urls=visited_urls,
                selectors_used=selectors_used,
                token_economics={
                    "creation_token_cost_estimate": 2000,
                    "repeated_execution_token_cost": 0,
                    "estimated_tokens_saved": 2000,
                },
                no_llm_used=True,
            )
    except ObjectNotFoundError as exc:
        return _failed_result(
            order_reference=order_reference,
            status="failed",
            decision="block",
            error_text=str(exc),
            steps=steps,
            visited_urls=visited_urls,
            selectors_used=selectors_used,
        )
    except BrowserRuntimeUnavailableError:
        raise
    except Exception as exc:
        return _failed_result(
            order_reference=order_reference,
            status="failed",
            decision="block",
            error_text=str(exc),
            steps=steps,
            visited_urls=visited_urls,
            selectors_used=selectors_used,
        )


def _failed_result(
    *,
    order_reference: str,
    status: str,
    decision: str,
    error_text: str,
    steps: list[BrowserSkillRunStepResult],
    visited_urls: list[str],
    selectors_used: list[str],
) -> BrowserSkillRunResult:
    return BrowserSkillRunResult(
        status=status,
        decision=decision,
        output={
            "order_reference": order_reference,
            "policy_id": "formula_guard",
            "policy_version": "0.1.0",
            "issues": [],
        },
        issues=[],
        steps=steps,
        visited_urls=visited_urls,
        selectors_used=selectors_used,
        token_economics={
            "creation_token_cost_estimate": 2000,
            "repeated_execution_token_cost": 0,
            "estimated_tokens_saved": 2000,
        },
        no_llm_used=True,
        error_text=error_text,
    )


def _extract_detail_values(page) -> dict[str, str]:
    metrics = page.locator(".metric")
    values: dict[str, str] = {}
    for index in range(metrics.count()):
        text = metrics.nth(index).inner_text().strip()
        lines = [line.strip() for line in text.splitlines() if line.strip()]
        if len(lines) >= 2:
            values[lines[0].rstrip(":")] = lines[1]
    return values


def _extract_formula_values(page) -> dict[str, str]:
    values: dict[str, str] = {}
    for text in page.locator(".row").all_inner_texts():
        lines = [line.strip() for line in text.splitlines() if line.strip()]
        if not lines:
            continue
        label, value = _split_label_value(lines[0])
        if label:
            values[label] = value
    status_text = page.locator("[data-testid='formula-status']").inner_text().strip()
    values["formula_status"] = status_text
    return values


def _split_label_value(text: str) -> tuple[str, str]:
    if ":" not in text:
        return text, ""
    label, value = text.split(":", 1)
    return label.strip(), value.strip()


def _build_sales_order(order_reference: str, detail_values: dict[str, str], formula_values: dict[str, str]) -> SalesOrder:
    customer_name = detail_values.get("Customer", "Fake Customer")
    state_value = detail_values.get("State", "draft")
    quantity = _to_decimal(formula_values.get("Quantity", detail_values.get("Order lines", "1")))
    capacity_ml = _to_decimal(formula_values.get("Capacity ml", "0"))
    formula_ml_per_unit = _to_decimal(formula_values.get("Formula ml per unit", "0"))
    formula_total_ml = _to_decimal(formula_values.get("Formula total ml", "0"))

    company = Company(id="company_fake_ui", native_id="fake_company_ui_1", name="Fake ERP Company", currency="EUR")
    customer = Customer(id="customer_fake_ui", native_id="fake_customer_ui_1", name=customer_name, active=True)
    product = Product(
        id="product_fake_ui",
        native_id="fake_product_ui_1",
        name=formula_values.get("Product name", "Fake Product"),
        sku="FAKE-UI",
        active=True,
        type=ProductType.STOCKABLE,
        tracking=ProductTracking.LOT,
        capacity_ml=capacity_ml,
    )
    line = SalesOrderLine(
        id="line_fake_ui_1",
        native_id="fake_line_ui_1",
        product=product,
        quantity=quantity,
        unit_price=Decimal("0"),
        subtotal=Decimal("0"),
        formula_lines=[FormulaLine(component_name="Captured Formula", ml=formula_ml_per_unit, ml_total=formula_total_ml)],
    )
    return SalesOrder(
        id="so_fake_ui_1",
        native_id="fake_so_ui_1",
        reference=order_reference,
        company=company,
        customer=customer,
        state=SalesOrderState(state_value) if state_value in SalesOrderState._value2member_map_ else SalesOrderState.DRAFT,
        currency="EUR",
        total_amount=Decimal("0"),
        lines=[line],
    )


def _to_decimal(value: str) -> Decimal:
    cleaned = value.strip().split()[0] if value.strip() else "0"
    try:
        return Decimal(cleaned)
    except Exception:
        return Decimal("0")