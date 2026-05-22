from __future__ import annotations

import json
import html
from decimal import Decimal
from urllib.parse import urlencode

from fastapi import APIRouter, Query
from fastapi.responses import HTMLResponse

from erpguard.adapters.fake import FakeERPAdapter
from erpguard.canonical.objects import SalesOrder, SalesOrderLine
from erpguard.product.ui_recorder_script import build_recorder_script


router = APIRouter(prefix="/fake-erp", tags=["fake-erp"])

ORDER_REFERENCES = [
    "SO-VALID",
    "SO-FORMULA-MISMATCH",
    "SO-CAPACITY-NO-FORMULA",
    "SO-EMPTY-LINES",
]


def _adapter() -> FakeERPAdapter:
    return FakeERPAdapter()


def _known_orders() -> list[SalesOrder]:
    adapter = _adapter()
    orders: list[SalesOrder] = []
    for reference in ORDER_REFERENCES:
        orders.append(adapter.get_sales_order_by_reference(reference))
    return orders


def _find_order(order_id: str) -> SalesOrder:
    adapter = _adapter()
    try:
        return adapter.get_sales_order_by_reference(order_id)
    except Exception:
        return adapter.get_sales_order(order_id)


def _layout(title: str, body: str) -> HTMLResponse:
    return HTMLResponse(
        f"""<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>{html.escape(title)}</title>
    <style>
      body {{ font-family: Arial, sans-serif; margin: 24px; color: #1f2937; }}
      .shell {{ max-width: 1100px; margin: 0 auto; }}
      h1, h2 {{ margin: 0 0 12px 0; }}
      table {{ width: 100%; border-collapse: collapse; margin-top: 16px; }}
      th, td {{ border: 1px solid #d1d5db; padding: 10px; text-align: left; vertical-align: top; }}
      th {{ background: #f3f4f6; }}
      .card {{ border: 1px solid #d1d5db; border-radius: 8px; padding: 16px; margin-top: 16px; background: #fff; }}
      .status {{ padding: 12px; border-radius: 8px; background: #f9fafb; border: 1px dashed #cbd5e1; }}
      .muted {{ color: #6b7280; }}
      .toolbar {{ display: flex; gap: 12px; align-items: center; margin: 16px 0; flex-wrap: wrap; }}
      input[type="search"] {{ padding: 10px 12px; min-width: 320px; }}
      a.button, button {{ display: inline-block; padding: 8px 12px; border-radius: 6px; border: 1px solid #111827; background: #111827; color: white; text-decoration: none; cursor: pointer; }}
      .button.secondary {{ background: white; color: #111827; }}
      .grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: 12px; }}
      .metric {{ padding: 12px; background: #f9fafb; border-radius: 8px; }}
      .ok {{ color: #166534; }}
      .warn {{ color: #92400e; }}
      .bad {{ color: #991b1b; }}
      .row {{ margin-bottom: 10px; }}
    </style>
  </head>
  <body>
    <div class="shell">
      {body}
    </div>
  </body>
</html>""",
        media_type="text/html",
    )


def _format_decimal(value: Decimal | None) -> str:
    if value is None:
        return "-"
    normalized = value.normalize()
    if normalized == normalized.to_integral():
        return format(normalized.quantize(Decimal("1")), "f")
    return format(normalized, "f")


def _first_line(order: SalesOrder) -> SalesOrderLine | None:
    return order.lines[0] if order.lines else None


def _recording_url(path: str, recording_id: str | None, rsid: str | None = None, **params: str | None) -> str:
    query: dict[str, str] = {key: value for key, value in params.items() if value is not None}
    if recording_id:
        query["recording_id"] = recording_id
    if rsid:
        query["rsid"] = rsid
    if not query:
        return path
    return f"{path}?{urlencode(query)}"


def _recording_hidden_input(recording_id: str | None, rsid: str | None = None) -> str:
    parts = []
    if recording_id:
        parts.append(f'<input type="hidden" name="recording_id" value="{html.escape(recording_id)}">')
    if rsid:
        parts.append(f'<input type="hidden" name="rsid" value="{html.escape(rsid)}">')
    return "".join(parts)


def _recording_script(recording_id: str | None) -> str:
    if not recording_id:
        return ""

    recording_id_json = json.dumps(recording_id)
    return f"""
      <script>
        (() => {{
          const recordingId = {recording_id_json};
          const endpoint = `/v1/recordings/${{recordingId}}/events`;
          const sessionKey = "erpguard_human_recording_v0_2";

          const bodyText = () => document.body ? document.body.innerText.trim() : "";

          const postEvent = (payload) => {{
            try {{
              const blob = new Blob([JSON.stringify(payload)], {{ type: "application/json" }});
              if (navigator.sendBeacon(endpoint, blob)) {{
                return;
              }}
            }} catch (error) {{
              console.warn("Beacon recording failed", error);
            }}

            fetch(endpoint, {{
              method: "POST",
              headers: {{ "Content-Type": "application/json" }},
              body: JSON.stringify(payload),
              keepalive: true,
            }}).catch((error) => console.warn("Recording event failed", error));
          }};

          const capture = (eventType, selector, extra = {{}}) => {{
            postEvent({{
              event_type: eventType,
              url: window.location.href,
              page_title: document.title,
              element_role: extra.element_role ?? null,
              element_text: extra.element_text ?? null,
              selector,
              input_value: extra.input_value ?? null,
              before_text_snapshot: extra.before_text_snapshot ?? null,
              after_text_snapshot: extra.after_text_snapshot ?? null,
              metadata_json: {{ source: "human_recording_v0_2" }},
            }});
          }};

          const attach = () => {{
            if (sessionStorage.getItem(sessionKey) !== recordingId) {{
              sessionStorage.setItem(sessionKey, recordingId);
              capture("navigate", null, {{ before_text_snapshot: "", after_text_snapshot: bodyText() }});
            }}

            const orderSearch = document.querySelector("[data-testid='order-search']");
            if (orderSearch) {{
              orderSearch.addEventListener("change", (event) => {{
                capture("fill", "[data-testid='order-search']", {{
                  element_role: "searchbox",
                  element_text: event.target.value,
                  input_value: event.target.value,
                  before_text_snapshot: bodyText(),
                  after_text_snapshot: bodyText(),
                }});
              }});
            }}

            document.querySelectorAll("[data-testid^='open-order-']").forEach((element) => {{
              element.addEventListener("click", () => {{
                const testId = element.getAttribute("data-testid");
                capture("click", testId ? `[data-testid='${{testId}}']` : null, {{
                  element_role: "link",
                  element_text: element.innerText.trim(),
                  before_text_snapshot: bodyText(),
                  after_text_snapshot: bodyText(),
                }});
              }});
            }});

            const formulaTab = document.querySelector("[data-testid='formula-tab']");
            if (formulaTab) {{
              formulaTab.addEventListener("click", () => {{
                capture("click", "[data-testid='formula-tab']", {{
                  element_role: "link",
                  element_text: formulaTab.innerText.trim(),
                  before_text_snapshot: bodyText(),
                  after_text_snapshot: bodyText(),
                }});
              }});
            }}

            const reviewFormula = document.querySelector("[data-testid='review-formula']");
            if (reviewFormula) {{
              reviewFormula.addEventListener("click", () => {{
                capture("click", "[data-testid='review-formula']", {{
                  element_role: "button",
                  element_text: reviewFormula.innerText.trim(),
                  before_text_snapshot: bodyText(),
                  after_text_snapshot: bodyText(),
                }});
              }});
            }}
          }};

          if (document.readyState === "loading") {{
            document.addEventListener("DOMContentLoaded", attach);
          }} else {{
            attach();
          }}
        }})();
      </script>
    """


def _r2s_recorder_script(rsid: str | None) -> str:
    if not rsid:
        return ""
    return build_recorder_script(rsid)


@router.get("/sales/orders", response_class=HTMLResponse)
def sales_orders_page(
  q: str | None = Query(default=None, alias="q"),
  recording_id: str | None = Query(default=None),
  rsid: str | None = Query(default=None),
) -> HTMLResponse:
    orders = _known_orders()
    if q:
        query = q.casefold()
        orders = [
            order
            for order in orders
            if query in order.reference.casefold()
            or (order.customer and query in order.customer.name.casefold())
            or query in order.state.value.casefold()
        ]

    rows = []
    for order in orders:
        rows.append(
            f"""
            <tr data-testid="order-row-{html.escape(order.reference)}">
              <td>{html.escape(order.reference)}</td>
              <td>{html.escape(order.customer.name if order.customer else '-')}</td>
              <td>{html.escape(order.state.value)}</td>
              <td>{len(order.lines)}</td>
              <td><a class="button"
                     data-testid="open-order-{html.escape(order.reference)}"
                     aria-label="Open order {html.escape(order.reference)}"
                     href="{_recording_url(f'/fake-erp/sales/orders/{html.escape(order.reference)}', recording_id, rsid)}">Open order</a></td>
            </tr>
            """
        )

    body = f"""
      <h1>Fake ERP Sales Orders</h1>
      <p class="muted">Local demo surface for Record-to-Skill and Formula Guard scenarios.</p>
      <form class="toolbar" method="get" action="/fake-erp/sales/orders" role="search" aria-label="Search sales orders">
        <label for="order-search">Search order</label>
        <input id="order-search"
               data-testid="order-search"
               type="search"
               name="q"
               value="{html.escape(q or '')}"
               placeholder="Search order"
               aria-label="Search orders">
        {_recording_hidden_input(recording_id, rsid)}
      </form>
      <table role="grid" aria-label="Sales orders list">
        <thead>
          <tr>
            <th scope="col">Reference</th>
            <th scope="col">Customer</th>
            <th scope="col">State</th>
            <th scope="col">Lines</th>
            <th scope="col">Action</th>
          </tr>
        </thead>
        <tbody>
          {''.join(rows)}
        </tbody>
      </table>
      {_recording_script(recording_id)}
      {_r2s_recorder_script(rsid)}
    """
    return _layout("Fake ERP Sales Orders", body)


@router.get("/sales/orders/{order_id}", response_class=HTMLResponse)
def sales_order_detail(
    order_id: str,
    recording_id: str | None = Query(default=None),
    rsid: str | None = Query(default=None),
) -> HTMLResponse:
    order = _find_order(order_id)
    line = _first_line(order)
    status_text = "No order lines available" if line is None else "Formula ready for review"
    lines_html = "<p class='muted'>No order lines.</p>" if not order.lines else "".join(
        f"""
        <tr>
          <td>{html.escape(order_line.product.name)}</td>
          <td>{_format_decimal(order_line.quantity)}</td>
          <td>{_format_decimal(order_line.product.capacity_ml)}</td>
          <td>{_format_decimal(order_line.unit_price)}</td>
          <td>{_format_decimal(order_line.subtotal)}</td>
        </tr>
        """
        for order_line in order.lines
    )

    body = f"""
      <h1 data-testid="order-detail-title">{html.escape(order.reference)}</h1>
      <div class="grid">
        <div class="metric" data-testid="order-customer"><strong>Customer</strong><div>{html.escape(order.customer.name if order.customer else '-')}</div></div>
        <div class="metric" data-testid="order-state"><strong>State</strong><div>{html.escape(order.state.value)}</div></div>
        <div class="metric" data-testid="order-line-count"><strong>Order lines</strong><div>{len(order.lines)}</div></div>
      </div>
      <div class="card">
        <h2>Order lines</h2>
        <table role="grid" aria-label="Order lines">
          <thead>
            <tr>
              <th scope="col">Product</th>
              <th scope="col">Quantity</th>
              <th scope="col">Capacity ml</th>
              <th scope="col">Unit price</th>
              <th scope="col">Subtotal</th>
            </tr>
          </thead>
          <tbody>
            {lines_html}
          </tbody>
        </table>
      </div>
      <div class="card status" data-testid="order-status-result" aria-label="Order status result">
        <strong>Status / Result</strong>
        <div>{html.escape(status_text)}</div>
      </div>
      <p class="toolbar">
        <a class="button secondary"
           data-testid="formula-tab"
           aria-label="Formula tab"
           href="{_recording_url(f'/fake-erp/sales/orders/{html.escape(order.reference)}/formula', recording_id, rsid)}">Formula tab</a>
      </p>
      {_recording_script(recording_id)}
      {_r2s_recorder_script(rsid)}
    """
    return _layout(f"Fake ERP Order {order.reference}", body)


@router.get("/sales/orders/{order_id}/formula", response_class=HTMLResponse)
def sales_order_formula(
    order_id: str,
    recording_id: str | None = Query(default=None),
    rsid: str | None = Query(default=None),
) -> HTMLResponse:
    order = _find_order(order_id)
    line = _first_line(order)

    if line is None:
        status_text = "Invalid: no order lines available"
        formula_details = "<p class='bad'>This order has no lines to validate.</p>"
        product_name = "-"
        quantity = "-"
        capacity_ml = "-"
        formula_ml_per_unit = "-"
        formula_total_ml = "-"
    else:
        validation = line.formula_validation
        is_valid = validation.is_valid if validation is not None else False
        if validation is None:
            status_text = "Invalid: formula data missing"
            formula_details = "<p class='warn'>No formula lines are defined for this product.</p>"
        elif is_valid:
            status_text = "Valid: formula matches product capacity"
            formula_details = "<p class='ok'>Formula data is valid.</p>"
        else:
            status_text = f"Invalid: {validation.message or 'formula does not match'}"
            formula_details = f"<p class='bad'>{html.escape(validation.message or 'Formula validation failed.')}</p>"

        product_name = line.product.name
        quantity = _format_decimal(line.quantity)
        capacity_ml = _format_decimal(line.product.capacity_ml)
        formula_ml_per_unit = _format_decimal(
            validation.actual_ml_per_unit if validation is not None else None
        )
        formula_total_ml = _format_decimal(validation.actual_total_ml if validation is not None else None)

    body = f"""
      <h1>Formula Tab - {html.escape(order.reference)}</h1>
      <div class="card">
        <div class="row"><strong>Product name:</strong> {html.escape(product_name)}</div>
        <div class="row"><strong>Quantity:</strong> {html.escape(quantity)}</div>
        <div class="row"><strong>Capacity ml:</strong> {html.escape(capacity_ml)}</div>
        <div class="row"><strong>Formula ml per unit:</strong> {html.escape(formula_ml_per_unit)}</div>
        <div class="row"><strong>Formula total ml:</strong> {html.escape(formula_total_ml)}</div>
      </div>
      <div class="card status" data-testid="formula-status">
        <strong>Formula status</strong>
        <div>{html.escape(status_text)}</div>
        {formula_details}
      </div>
      <p class="toolbar">
        <button data-testid="review-formula"
                aria-label="Review formula"
                name="review-formula"
                type="button">Review formula</button>
      </p>
      {_recording_script(recording_id)}
      {_r2s_recorder_script(rsid)}
    """
    return _layout(f"Fake ERP Formula {order.reference}", body)