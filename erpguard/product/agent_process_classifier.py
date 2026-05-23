from __future__ import annotations

from pydantic import BaseModel, Field


_PROCESS_MAP: dict[str, dict] = {
    "accounting_cycle": {
        "entities": {"invoice", "payment"},
        "actions": {"validate", "confirm", "send", "report", "read"},
        "description": "Financial transactions: invoices, payments, reconciliation",
    },
    "inventory_management": {
        "entities": {"inventory"},
        "actions": {"read", "update", "create", "report"},
        "description": "Stock control: levels, transfers, adjustments",
    },
    "sales_cycle": {
        "entities": {"sales_order", "invoice", "partner", "payment"},
        "actions": {"create", "confirm", "validate", "send", "update", "read"},
        "description": "End-to-end sales process: quotations, orders, invoicing, payment",
    },
    "purchase_cycle": {
        "entities": {"purchase_order", "partner", "product", "inventory"},
        "actions": {"create", "confirm", "update", "read"},
        "description": "End-to-end purchase process: RFQ, PO, receipt, billing",
    },
    "customer_management": {
        "entities": {"partner"},
        "actions": {"read", "update", "create", "report", "send"},
        "description": "Customer and vendor master data management",
    },
    "product_management": {
        "entities": {"product"},
        "actions": {"read", "update", "create"},
        "description": "Product catalogue and pricing management",
    },
    "reporting": {
        "entities": {"sales_order", "invoice", "purchase_order", "inventory", "partner", "product", "payment"},
        "actions": {"report", "read"},
        "description": "Business intelligence and reporting",
    },
}


class ProcessClassificationResult(BaseModel):
    process_category: str = "general"
    process_description: str = "General ERP automation"
    confidence: str = "low"
    candidate_categories: list[str] = Field(default_factory=list)


def classify_process(action_type: str, target_entity: str) -> ProcessClassificationResult:
    scored: list[tuple[str, int]] = []
    for category, config in _PROCESS_MAP.items():
        entity_match = target_entity in config["entities"]
        action_match = action_type in config["actions"]
        score = (2 if entity_match else 0) + (1 if action_match else 0)
        if score > 0:
            scored.append((category, score))

    scored.sort(key=lambda x: x[1], reverse=True)

    if not scored:
        return ProcessClassificationResult(
            process_category="general",
            process_description="General ERP automation",
            confidence="low",
            candidate_categories=[],
        )

    best_category, best_score = scored[0]
    confidence = "high" if best_score == 3 else ("medium" if best_score >= 1 else "low")
    return ProcessClassificationResult(
        process_category=best_category,
        process_description=_PROCESS_MAP[best_category]["description"],
        confidence=confidence,
        candidate_categories=[c for c, _ in scored[:3]],
    )
