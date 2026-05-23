from __future__ import annotations

from pydantic import BaseModel, Field


_ACTION_KEYWORDS: dict[str, list[str]] = {
    "read": ["check", "show", "list", "display", "view", "get", "fetch", "read", "find", "search", "lookup", "retrieve"],
    "validate": ["validate", "verify", "preflight", "guard", "ensure", "review formula", "formula check"],
    "report": ["report", "export", "summarize", "aggregate", "statistics", "dashboard", "summary report", "generate a report", "generate report"],
    "create": ["create", "add", "new", "register", "generate", "insert", "open"],
    "update": ["update", "edit", "modify", "change", "set", "correct", "fix"],
    "send": ["send", "email", "notify", "alert", "message", "remind", "communicate"],
    "confirm": ["confirm", "approve", "finalize", "sign off", "close", "authorize"],
    "delete": ["delete", "remove", "cancel", "discard", "void"],
}

_ENTITY_KEYWORDS: dict[str, list[str]] = {
    "sales_order": ["sales order", "sale order", "customer order", "quotation", "quote", " so ", "pedido", "venta"],
    "invoice": ["invoice", "bill", "billing", "factura", "receipt", "credit note"],
    "partner": ["partner", "customer", "vendor", "supplier", "client", "contact", "company"],
    "product": ["product", "item", "article", "sku", "service", "catalogue"],
    "purchase_order": ["purchase order", " po ", "vendor order", "compra"],
    "inventory": ["inventory", "stock", "warehouse", "location", "lot", "serial"],
    "payment": ["payment", "collect", "cobro", "paid", "remittance"],
    "employee": ["employee", "staff", "hr", "payroll", "leave"],
    "project": ["project", "task", "milestone", "timesheet"],
}

_TRIGGER_KEYWORDS: dict[str, list[str]] = {
    "scheduled": ["every day", "daily", "weekly", "monthly", "at midnight", "at noon", "every morning",
                  "every week", "scheduled", "cron", "every hour", "each day", "each week"],
    "event_driven": ["when ", "if ", "on create", "on update", "on confirm", "trigger", "upon", "after", "once "],
    "manual": ["manually", "on demand", "when i click", "button", "run", "start", "launch"],
}


class IntentAnalysisResult(BaseModel):
    action_type: str = "unknown"
    target_entity: str = "unknown"
    trigger_type: str = "manual"
    confidence: str = "low"
    matched_keywords: list[str] = Field(default_factory=list)
    is_advisory_only: bool = True
    can_execute: bool = False


def analyze_intent(request_text: str) -> IntentAnalysisResult:
    text_lower = f" {request_text.lower()} "

    action_type = "unknown"
    action_keywords: list[str] = []
    for action, keywords in _ACTION_KEYWORDS.items():
        matched = [kw for kw in keywords if kw in text_lower]
        if matched:
            action_type = action
            action_keywords = matched
            break

    target_entity = "unknown"
    entity_keywords: list[str] = []
    for entity, keywords in _ENTITY_KEYWORDS.items():
        matched = [kw for kw in keywords if kw in text_lower]
        if matched:
            target_entity = entity
            entity_keywords = matched
            break

    trigger_type = "manual"
    for trigger, keywords in _TRIGGER_KEYWORDS.items():
        if any(kw in text_lower for kw in keywords):
            trigger_type = trigger
            break

    all_matched = action_keywords + entity_keywords
    if action_type != "unknown" and target_entity != "unknown":
        confidence = "high"
    elif action_type != "unknown" or target_entity != "unknown":
        confidence = "medium"
    else:
        confidence = "low"

    return IntentAnalysisResult(
        action_type=action_type,
        target_entity=target_entity,
        trigger_type=trigger_type,
        confidence=confidence,
        matched_keywords=all_matched,
        is_advisory_only=True,
        can_execute=False,
    )
