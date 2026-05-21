from __future__ import annotations

from typing import Any

from erpguard.adapters.odoo.config import OdooConfig
from erpguard.adapters.odoo.field_discovery import detect_capacity_field, detect_formula_model, is_custom_field
from erpguard.adapters.odoo.readonly_client import OdooReadOnlyClient

CORE_MODELS = [
    "res.users",
    "ir.module.module",
    "ir.model",
    "ir.model.fields",
    "sale.order",
    "sale.order.line",
    "product.product",
    "product.template",
    "res.partner",
    "stock.quant",
    "stock.move",
    "stock.picking",
    "mrp.production",
    "mrp.bom",
    "account.move",
]

IMPORTANT_FIELDS_BY_MODEL = {
    "sale.order": ["id", "name", "state", "partner_id", "order_line", "amount_total"],
    "sale.order.line": ["id", "order_id", "product_id", "product_uom_qty", "price_unit", "price_subtotal"],
    "product.product": ["id", "display_name", "default_code", "tracking", "standard_price"],
    "product.template": ["id", "display_name", "default_code", "tracking", "standard_price"],
    "x_sale_formula_line": [
        "x_studio_fragancia_id",
        "x_studio_ml_por_unidad",
        "x_studio_ml_total_pedido",
        "x_studio_sale_line_id",
    ],
}

MODULE_ALIASES = {
    "sale": {"sale", "sale_management", "sale_stock"},
    "stock": {"stock"},
    "mrp": {"mrp"},
    "account": {"account"},
}


class OdooDiagnosisService:
    def __init__(self, client: OdooReadOnlyClient, config: OdooConfig) -> None:
        self.client = client
        self.config = config

    def run(self, include_samples: bool = True, sample_limits: Any | None = None) -> dict[str, Any]:
        sample_limits = sample_limits or {"sales_orders": 5, "products": 5, "custom_fields": 50}
        version = self.client.version()
        uid = self.client.authenticate()

        modules = self._check_modules()
        models = self._check_models()
        fields = self._check_fields(models)
        custom_models = self._detect_custom_models(models)
        capacity_detection = detect_capacity_field(
            fields.get("product.product", {}).get("raw", {}),
            self.config.capacity_field,
            fields.get("product.template", {}).get("raw", {}),
        )
        formula_detection = detect_formula_model(custom_models, self.config.formula_model)

        sales_samples = self._get_sales_order_samples(sample_limits["sales_orders"]) if include_samples else []
        product_samples = (
            self._get_product_samples(sample_limits["products"], capacity_detection.get("field_name"))
            if include_samples
            else []
        )
        custom_fields = self._detect_custom_fields(fields, sample_limits["custom_fields"])
        warnings = self._build_warnings(modules, fields, capacity_detection, formula_detection)

        return {
            "status": "ok",
            "read_only_mode": True,
            "odoo": {
                "server_version": version.get("server_version"),
                "uid": uid,
            },
            "modules": modules,
            "models": {
                "core_detected": [model for model, snapshot in models.items() if snapshot["exists"] and not model.startswith("x_")],
                "custom_detected": custom_models,
            },
            "fields": fields,
            "samples": {
                "sales_orders": sales_samples,
                "products": product_samples,
            },
            "detected": {
                "installed_modules": [name for name, installed in modules.items() if installed],
                "core_models": [model for model in CORE_MODELS if models.get(model, {}).get("exists")],
                "custom_models": custom_models,
                "custom_fields": custom_fields,
                "sales_orders_sample_count": len(sales_samples),
                "products_sample_count": len(product_samples),
            },
            "warnings": warnings,
            "next_recommended_action": self._next_recommended_action(warnings, formula_detection),
        }

    def _check_modules(self) -> dict[str, bool]:
        try:
            module_rows = self.client.search_read("ir.module.module", [["state", "=", "installed"]], ["name", "state"])
        except Exception:
            return {alias: False for alias in MODULE_ALIASES}

        installed = {str(row.get("name")) for row in module_rows if row.get("name")}
        modules: dict[str, bool] = {}
        for alias, candidates in MODULE_ALIASES.items():
            modules[alias] = any(candidate in installed for candidate in candidates)
        return modules

    def _check_models(self) -> dict[str, dict[str, Any]]:
        available_models = self._fetch_available_models()
        result: dict[str, dict[str, Any]] = {}
        for model in CORE_MODELS:
            result[model] = {
                "exists": model in available_models,
                "readable": False,
                "status": "missing" if model not in available_models else "unknown",
            }
        return result

    def _fetch_available_models(self) -> set[str]:
        try:
            rows = self.client.search_read(
                "ir.model",
                [["model", "in", CORE_MODELS]],
                ["model", "name"],
                limit=len(CORE_MODELS),
            )
            return {str(row.get("model")) for row in rows if row.get("model")}
        except Exception:
            return set()

    def _check_fields(self, models: dict[str, dict[str, Any]]) -> dict[str, dict[str, Any]]:
        snapshots: dict[str, dict[str, Any]] = {}
        model_names = list(dict.fromkeys([*CORE_MODELS, self.config.formula_model]))
        for model in model_names:
            snapshots[model] = self._fetch_field_snapshot(model)
            if model in models and snapshots[model]["status"] == "ok":
                models[model]["readable"] = True
                models[model]["status"] = "ok"
            elif model in models and snapshots[model]["status"] == "permission_denied":
                models[model]["readable"] = False
                models[model]["status"] = "permission_denied"
        return snapshots

    def _fetch_field_snapshot(self, model: str) -> dict[str, Any]:
        try:
            metadata = self.client.fields_get(model, attributes=["string", "type", "readonly", "required", "relation"])
        except Exception as exc:
            return {
                "exists": False,
                "readable": False,
                "status": self._classify_error_status(exc),
                "important_fields": [],
                "custom_fields": [],
                "raw": {},
            }

        field_names = list(metadata.keys())
        important_fields = [field_name for field_name in IMPORTANT_FIELDS_BY_MODEL.get(model, []) if field_name in metadata]
        custom_fields = [field_name for field_name in field_names if is_custom_field(field_name)]
        return {
            "exists": True,
            "readable": True,
            "status": "ok",
            "important_fields": important_fields,
            "custom_fields": custom_fields,
            "raw": metadata,
        }

    def _detect_custom_models(self, models: dict[str, dict[str, Any]]) -> list[str]:
        discovered = self._fetch_custom_model_names()
        return sorted(dict.fromkeys(model for model in discovered if model.startswith("x_")))

    def _fetch_custom_model_names(self) -> list[str]:
        try:
            rows = self.client.search_read("ir.model", [["model", "like", "x_%"]], ["model"], limit=200)
        except Exception:
            rows = []
        names = [str(row.get("model")) for row in rows if row.get("model")]
        return names

    def _detect_custom_fields(self, fields: dict[str, dict[str, Any]], limit: int) -> list[str]:
        seen: list[str] = []
        for snapshot in fields.values():
            for field_name in snapshot.get("custom_fields", []):
                if field_name not in seen:
                    seen.append(field_name)
                if len(seen) >= limit:
                    return seen
        return seen

    def _get_sales_order_samples(self, limit: int) -> list[dict[str, Any]]:
        rows = self.client.search_read(
            "sale.order",
            [],
            ["id", "name", "state", "order_line"],
            limit=limit,
        )
        return [
            {
                "id": row.get("id"),
                "name": row.get("name"),
                "state": row.get("state"),
                "line_count": len(row.get("order_line", [])),
            }
            for row in rows
        ]

    def _get_product_samples(self, limit: int, capacity_field: str | None) -> list[dict[str, Any]]:
        fields = ["id", "display_name", "default_code"]
        if capacity_field:
            fields.append(capacity_field)
        rows = self.client.search_read("product.product", [], fields, limit=limit)
        samples: list[dict[str, Any]] = []
        for row in rows:
            samples.append(
                {
                    "id": row.get("id"),
                    "display_name": row.get("display_name"),
                    "default_code": row.get("default_code"),
                    "capacity_ml": row.get(capacity_field) if capacity_field else None,
                }
            )
        return samples

    def _build_warnings(
        self,
        modules: dict[str, bool],
        fields: dict[str, dict[str, Any]],
        capacity_detection: dict[str, Any],
        formula_detection: dict[str, Any],
    ) -> list[dict[str, str]]:
        warnings: list[dict[str, str]] = []
        if not modules.get("sale", False):
            warnings.append(
                {
                    "code": "missing_sales_module",
                    "severity": "warning",
                    "message": "Sales module was not detected. Sales order preflight may not be available.",
                }
            )
        if self.config.capacity_field and not capacity_detection.get("configured_found", False):
            warnings.append(
                {
                    "code": "capacity_field_missing",
                    "severity": "warning",
                    "message": "Configured capacity field was not found on product.product or product.template.",
                }
            )
        required_formula_mappings = [
            "formula_sale_line_id",
            "formula_fragrance_id",
            "formula_ml_per_unit",
            "formula_ml_total",
        ]
        if self.config.formula_model and not formula_detection.get("configured_found", False):
            warnings.append(
                {
                    "code": "formula_model_missing",
                    "severity": "warning",
                    "message": "Configured formula model was not found.",
                }
            )
        if formula_detection.get("found", False):
            mappings = self.config.field_mappings or {}
            if any(not mappings.get(name) for name in required_formula_mappings):
                warnings.append(
                    {
                        "code": "formula_mapping_incomplete",
                        "severity": "warning",
                        "message": "Formula model exists but required formula field mappings are incomplete.",
                    }
                )
        if any(snapshot.get("status") == "permission_denied" for snapshot in fields.values()):
            warnings.append(
                {
                    "code": "read_permission_limited",
                    "severity": "warning",
                    "message": "The Odoo user cannot read one or more relevant models.",
                }
            )
        return warnings

    def _next_recommended_action(self, warnings: list[dict[str, str]], formula_detection: dict[str, Any]) -> str:
        warning_codes = {warning["code"] for warning in warnings}
        if "formula_model_missing" in warning_codes:
            return "Confirm the formula model and rerun diagnosis."
        if "formula_mapping_incomplete" in warning_codes:
            return "Configure field mappings for formula validation."
        if "missing_sales_module" in warning_codes:
            return "Install the Sales module before continuing."
        if "capacity_field_missing" in warning_codes:
            return "Configure the product capacity field."
        if formula_detection.get("found", False):
            return "Run read-only sales order canonical mapping."
        return "Confirm Odoo field mappings and rerun diagnosis."

    def _classify_error_status(self, exc: Exception) -> str:
        message = str(exc).lower()
        if "permission" in message or "access" in message or "denied" in message:
            return "permission_denied"
        return "error"
