from __future__ import annotations

from typing import Any

CUSTOM_FIELD_PREFIXES = ("x_", "x_studio_")
COMMON_CAPACITY_FIELD_CANDIDATES = (
    "x_studio_capacidad_ml",
    "x_capacity_ml",
    "capacity_ml",
    "x_capacity",
)
COMMON_FORMULA_MODEL_CANDIDATES = (
    "x_sale_formula_line",
    "x.sale.formula.line",
)


def is_custom_field(field_name: str) -> bool:
    return field_name.startswith(CUSTOM_FIELD_PREFIXES)


def detect_capacity_field(
    product_product_fields: dict[str, dict[str, Any]],
    configured_field: str | None,
    product_template_fields: dict[str, dict[str, Any]] | None = None,
) -> dict[str, Any]:
    configured_found = False
    sources = [
        (configured_field, "configured"),
        *[(candidate, "common") for candidate in COMMON_CAPACITY_FIELD_CANDIDATES],
    ]
    for candidate, source in sources:
        if candidate and candidate in product_product_fields:
            return {
                "field_name": candidate,
                "found": True,
                "configured_found": source == "configured",
                "source": source,
                "model": "product.product",
            }
        if candidate and product_template_fields and candidate in product_template_fields:
            return {
                "field_name": candidate,
                "found": True,
                "configured_found": source == "configured",
                "source": source,
                "model": "product.template",
            }
    return {
        "field_name": configured_field,
        "found": False,
        "configured_found": configured_found,
        "source": "missing",
        "model": None,
    }


def detect_formula_model(custom_models: list[str], configured_model: str | None) -> dict[str, Any]:
    candidate_models = list(dict.fromkeys([value for value in [configured_model, *COMMON_FORMULA_MODEL_CANDIDATES] if value]))
    for model_name in candidate_models:
        if model_name in custom_models:
            return {
                "model_name": model_name,
                "found": True,
                "configured_found": model_name == configured_model,
                "source": "configured" if model_name == configured_model else "common",
            }
    for model_name in custom_models:
        if "formula" in model_name.lower():
            return {
                "model_name": model_name,
                "found": True,
                "configured_found": False,
                "source": "heuristic",
            }
    return {
        "model_name": configured_model,
        "found": False,
        "configured_found": False,
        "source": "missing",
    }
