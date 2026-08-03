from __future__ import annotations

from collections.abc import Callable
from decimal import Decimal

from erpguard.connectors.odoo.transports import OdooReadTransport
from erpguard.connectors.odoo.write_transport import OdooWriteTransport
from erpguard.config import settings
from erpguard.connectors.sdk.models import (
    AuthSchema,
    CanonicalOperation,
    CapabilityDefinition,
    ConnectionTestResult,
    ConnectorContext,
    ConnectorFeatures,
    ConnectorMetadata,
    ConnectorSafetyFlags,
    DiscoveredSystemSchema,
    EventBatch,
    ExecutionPermit,
    IngestionCursor,
    NativeExecutionPlan,
    NativeExecutionResult,
    PullEventsRequest,
    ReadObjectsRequest,
    ReadObjectsResult,
    SystemFingerprint,
    VerificationResult,
    stable_digest,
)
from erpguard.connectors.sdk.template import ConnectorTemplate
from erpguard.domain.declared_capabilities.denylist import is_denylisted
from erpguard.domain.processes.candidate_integrity import stable_digest as stable_json_digest
from erpguard.domain.execution.side_effects import (
    ConfirmationControlContract,
    default_compensation_plan,
    default_confirmation_budget,
    evaluate_confirmation_effects,
    fingerprint_from_evidence,
)


class OdooConnectorPlugin(ConnectorTemplate):
    metadata = ConnectorMetadata(
        connector_id="odoo",
        package_name="erpguard",
        version="2.0.0",
        display_name="Odoo Connector v2",
        vendor="Odoo",
        system_types=["odoo"],
        supported_versions=["19"],
        plugin_api_version="2",
        features=ConnectorFeatures(
            object_read=True, schema_discovery=True, permission_inspection=True,
            fingerprint=True, verification=True, controlled_write=True,
        ),
    )

    MODELS = {
        "customer": ("res.partner", ["id", "name", "email"]),
        "product": ("product.product", ["id", "name", "default_code"]),
        "quote": ("sale.order", ["id", "name", "partner_id", "amount_total", "state"]),
    }

    def __init__(
        self,
        transport_factory: Callable[[ConnectorContext], OdooReadTransport] | None = None,
        write_transport_factory: Callable[[ConnectorContext], OdooWriteTransport] | None = None,
    ):
        self._transport_factory = transport_factory
        self._write_transport_factory = write_transport_factory

    def auth_schemas(self) -> list[AuthSchema]:
        return [AuthSchema(name="credential_ref", kind="secret_reference")]

    def capability_definitions(self) -> list[CapabilityDefinition]:
        read_only = [
            CapabilityDefinition(name=name, version="1", safety_tier="read_only")
            for name in ("customer.read", "product.read", "quote.read", "odoo.schema.discover", "odoo.permissions.inspect")
        ]
        # The only write-capable capabilities are the two bounded bridge
        # methods delivered in Phases 16 and 17. There is still no generic
        # Odoo model/method execution path.
        write_capable = [
            CapabilityDefinition(
                name="quote.create_draft", version="1", safety_tier="write_scoped_draft_only", supports_execution=True
            ),
            CapabilityDefinition(
                name="sales.order.confirm",
                version="1",
                safety_tier="R3_governed_staging_only",
                description="Confirm one unchanged staging sale order under a bound R3 permit.",
                supports_execution=True,
            ),
            CapabilityDefinition(
                name="sales.quote.create_pricing_scenario_draft",
                version="1",
                safety_tier="write_scoped_draft_only",
                description=(
                    "Create one controlled Odoo draft quotation scenario carrying "
                    "governed-recommendation pricing evidence (Spec 92 Sec 8). "
                    "Distinct from quote.create_draft: this path additionally "
                    "verifies customer/product/company preconditions and margin "
                    "postconditions against the recommendation's evidence."
                ),
                supports_execution=True,
            ),
        ]
        return read_only + write_capable

    def _transport(self, context: ConnectorContext) -> OdooReadTransport:
        factory = self._transport_factory or context.services.get("transport_factory")
        if factory is None:
            raise RuntimeError("odoo_transport_factory_required")
        return factory(context)

    def _write_transport(self, context: ConnectorContext) -> OdooWriteTransport:
        factory = self._write_transport_factory or context.services.get("write_transport_factory")
        if factory is None:
            raise RuntimeError("odoo_write_transport_factory_required")
        return factory(context)

    def _declared_capability(self, context: ConnectorContext, capability: str):
        lookup = context.services.get("declared_capability_lookup")
        if lookup is None:
            return None
        return lookup(capability.removeprefix("declared."))

    def _validate_declared_value(self, declared, value) -> str | None:
        """Re-validate a runtime value against the stored declaration --
        never trust the caller's declared type/range intent alone."""
        try:
            if declared.field_type == "integer":
                value = int(value)
            elif declared.field_type == "decimal":
                value = float(value)
            elif declared.field_type == "boolean":
                value = bool(value)
            else:
                value = str(value)
        except (TypeError, ValueError):
            return f"declared_capability_value_wrong_type:{declared.field_type}"
        if declared.allowed_values_json:
            import json as _json

            allowed_values = _json.loads(declared.allowed_values_json)
            if allowed_values and value not in allowed_values:
                return "declared_capability_value_not_allowed"
        caster = int if declared.field_type == "integer" else float
        if declared.field_type in {"integer", "decimal"}:
            if declared.minimum_value is not None and value < caster(declared.minimum_value):
                return "declared_capability_value_below_minimum"
            if declared.maximum_value is not None and value > caster(declared.maximum_value):
                return "declared_capability_value_above_maximum"
        return None

    async def test_connection(self, context: ConnectorContext) -> ConnectionTestResult:
        transport = self._transport(context)
        version = transport.version()
        transport.authenticate()
        return ConnectionTestResult(status="ok", summary=f"odoo_read_only:{version.get('server_version', 'unknown')}")

    async def discover_model_fields(self, context: ConnectorContext, model: str) -> dict[str, dict]:
        """Live field introspection for an arbitrary model, not limited to
        `MODELS` -- backs the schema-driven capability declaration UI so a
        user picks a real, currently-existing field instead of typing one
        blind. Read-only; no write-capability implication."""

        transport = self._transport(context)
        return transport.fields_get(model, ["string", "type", "readonly"])

    async def discover_schema(self, context: ConnectorContext) -> DiscoveredSystemSchema:
        transport = self._transport(context)
        fields: dict[str, list[str]] = {}
        for object_type, (model, defaults) in self.MODELS.items():
            discovered = transport.fields_get(model, ["string", "type", "readonly"])
            fields[object_type] = sorted(set(defaults).union(discovered.keys()))
        return DiscoveredSystemSchema(
            status="ok", objects=sorted(model for model, _ in self.MODELS.values()), fields=fields
        )

    async def fingerprint(self, context: ConnectorContext) -> SystemFingerprint:
        schema = await self.discover_schema(context)
        version = self._transport(context).version().get("server_version", "unknown")
        digest = stable_digest(version, *(f"{key}:{','.join(value)}" for key, value in sorted(schema.fields.items())))
        return SystemFingerprint(connector_id=self.metadata.connector_id, digest=digest, evidence={"version": version})

    async def pull_events(
        self, context: ConnectorContext, cursor: IngestionCursor | None, request: PullEventsRequest
    ) -> EventBatch:
        return EventBatch(status="blocked", events=[], next_cursor=cursor)

    async def read_objects(self, context: ConnectorContext, request: ReadObjectsRequest) -> ReadObjectsResult:
        if request.object_type not in self.MODELS:
            return ReadObjectsResult(status="blocked")
        model, fields = self.MODELS[request.object_type]
        identifiers = [int(value) for value in request.identifiers if value.isdigit()]
        records = self._transport(context).search_read(model, [["id", "in", identifiers]], fields)
        return ReadObjectsResult(status="ok", objects=records)

    async def plan_capability(
        self, context: ConnectorContext, operation: CanonicalOperation | str
    ) -> NativeExecutionPlan:
        capability = operation if isinstance(operation, str) else operation.capability
        arguments = {} if isinstance(operation, str) else operation.arguments
        if capability.startswith("declared."):
            declared = self._declared_capability(context, capability)
            if declared is None:
                return NativeExecutionPlan(capability=capability, status="blocked", steps=[], supports_execution=False)
            return NativeExecutionPlan(
                capability=capability,
                status="planned",
                steps=["odoo_read_field_before", "odoo_write_field", "odoo_read_field_after"],
                supports_execution=True,
                arguments=arguments,
            )
        definitions = {item.name: item for item in self.capability_definitions()}
        definition = definitions.get(capability)
        if definition is None:
            return NativeExecutionPlan(capability=capability, status="blocked", steps=[], supports_execution=False)
        if not definition.supports_execution:
            steps = ["odoo_read_only"]
        elif capability == "sales.order.confirm":
            steps = [
                "read_confirmation_snapshot",
                "verify_r3_permit_and_unchanged_state",
                "odoo_sale_order_action_confirm",
                "verify_confirmation_postconditions",
            ]
        elif capability == "sales.quote.create_pricing_scenario_draft":
            steps = [
                "verify_pricing_scenario_preconditions",
                "odoo_create_draft_quote_pricing_scenario",
                "verify_pricing_scenario_postconditions",
            ]
        else:
            steps = ["odoo_create_draft_quote"]
        return NativeExecutionPlan(
            capability=capability, status="planned", steps=steps,
            supports_execution=definition.supports_execution, arguments=arguments,
        )

    async def execute_capability(
        self, context: ConnectorContext, plan: NativeExecutionPlan, permit: ExecutionPermit
    ) -> NativeExecutionResult:
        if plan.capability.startswith("declared."):
            return self._execute_declared_field_write(context, plan)
        if plan.capability == "sales.order.confirm":
            return self._execute_governed_confirmation(context, plan, permit)
        if plan.capability == "sales.quote.create_pricing_scenario_draft":
            return self._execute_pricing_scenario_draft(context, plan)
        if plan.capability != "quote.create_draft":
            return NativeExecutionResult(
                status="blocked", summary="odoo_connector_v2_is_read_only",
                errors=["write_capability_not_declared"], safety_flags=ConnectorSafetyFlags(),
            )
        return self._execute_quote_create_draft(context, plan)

    def pricing_scenario_preflight(self, context: ConnectorContext, operation: CanonicalOperation) -> dict:
        """Spec 92 Sec 8.3 preconditions checked against live Odoo state --
        the recommendation/approval/feature-flag/margin-floor preconditions
        are already enforced in `erpguard.domain.recommendations.validation`
        before an action draft is ever built; this covers the ones that can
        only be verified against a live connection (staging-only, customer
        active, products active/saleable, no forbidden product marker)."""

        args = operation.arguments
        metadata = context.services.get("connection_metadata", {})
        environment = str(metadata.get("environment", "")).lower()
        marker = settings.odoo_confirmation_forbidden_marker.casefold()

        issues: list[str] = []
        if environment != "staging":
            issues.append("pricing_scenario_requires_staging_connection")

        transport = self._write_transport(context)
        try:
            partner_id = int(args["partner_id"])
        except (KeyError, TypeError, ValueError):
            issues.append("pricing_scenario_missing_partner_id")
            partner_id = None
        if partner_id is not None:
            try:
                partner = transport.read_partner(partner_id)
                if not partner.get("active", True):
                    issues.append("pricing_scenario_customer_inactive")
            except LookupError:
                issues.append("pricing_scenario_customer_not_found")

        product_ids: list[int] = []
        for line in args.get("lines", []):
            try:
                product_ids.append(int(line["product_id"]))
            except (KeyError, TypeError, ValueError):
                issues.append("pricing_scenario_line_missing_product_id")
        if product_ids:
            products = {product["id"]: product for product in transport.read_products(product_ids)}
            for product_id in product_ids:
                product = products.get(product_id)
                if product is None:
                    issues.append(f"pricing_scenario_product_not_found:{product_id}")
                    continue
                if not product.get("active", True) or not product.get("sale_ok", True):
                    issues.append(f"pricing_scenario_product_not_saleable:{product_id}")
                if marker and marker in str(product.get("name", "")).casefold():
                    issues.append(f"pricing_scenario_forbidden_product_marker:{product_id}")

        return {"status": "blocked" if issues else "passed", "issues": issues, "environment": environment}

    def governed_confirmation_snapshot(
        self, context: ConnectorContext, operation: CanonicalOperation
    ) -> dict:
        if operation.capability != "sales.order.confirm":
            raise ValueError("governed_snapshot_unsupported_capability")
        try:
            order_id = int(operation.arguments["order_id"])
        except (KeyError, TypeError, ValueError) as exc:
            raise ValueError("confirmation_requires_order_id") from exc
        return self._write_transport(context).read_confirmation_snapshot(order_id)

    def governed_confirmation_preflight(
        self,
        context: ConnectorContext,
        operation: CanonicalOperation,
        snapshot: dict,
        control_contract: dict | None = None,
    ) -> dict:
        """Return an R3 preflight report; any issue is a hard block."""

        metadata = context.services.get("connection_metadata", {})
        environment = str(metadata.get("environment", "")).lower()
        configured_ceiling = metadata.get(
            "confirmation_amount_ceiling",
            settings.odoo_confirmation_amount_ceiling,
        )
        try:
            ceiling = min(float(configured_ceiling), settings.odoo_confirmation_amount_ceiling)
        except (TypeError, ValueError):
            ceiling = settings.odoo_confirmation_amount_ceiling

        marker = settings.odoo_confirmation_forbidden_marker.casefold()
        searchable = [
            str(snapshot.get("name") or ""),
            str(snapshot.get("client_reference") or ""),
            *(str(line.get("product_name") or "") for line in snapshot.get("lines", [])),
        ]
        issues: list[str] = []
        if not settings.allow_odoo_governed_confirmation:
            issues.append("governed_confirmation_disabled")
        if environment != "staging":
            issues.append("confirmation_requires_staging_connection")
        if snapshot.get("state") not in {"draft", "sent"}:
            issues.append(f"confirmation_requires_draft_or_sent_state:{snapshot.get('state')}")
        if float(snapshot.get("amount_total") or 0) > ceiling:
            issues.append("confirmation_amount_exceeds_ceiling")
        if marker and any(marker in value.casefold() for value in searchable):
            issues.append("confirmation_forbidden_marker_detected")
        if snapshot.get("invoices"):
            issues.append("confirmation_preexisting_invoices")
        contract = (
            ConfirmationControlContract.model_validate(control_contract)
            if control_contract is not None
            else self.governed_confirmation_control_contract(context, operation, snapshot)
        )
        if not contract.automation_fingerprint.complete:
            issues.extend(contract.automation_fingerprint.blocking_issues)
        issues.extend(str(item) for item in snapshot.get("effect_observation_issues", []))

        predicted_effects = [
            {
                "effect": "sale_order_state_transition",
                "from": snapshot.get("state"),
                "to": "sale",
            },
            {
                "effect": "downstream_operations_may_be_created",
                "possible": ["stock_pickings", "procurements", "purchases", "manufacturing"],
                "certainty": "conservative_prediction",
            },
        ]
        return {
            "status": "blocked" if issues else "passed",
            "risk": "R3",
            "environment": environment,
            "amount_ceiling": ceiling,
            "issues": issues,
            "predicted_effects": predicted_effects,
            "control_contract_hash": contract.digest,
            "side_effect_budget": contract.side_effect_budget.model_dump(mode="json"),
            "automation_fingerprint": contract.automation_fingerprint.model_dump(mode="json"),
        }

    def governed_confirmation_control_contract(
        self,
        context: ConnectorContext,
        operation: CanonicalOperation,
        snapshot: dict,
    ) -> ConfirmationControlContract:
        order_id = int(snapshot["order_id"])
        evidence = self._write_transport(context).read_confirmation_automation_fingerprint(order_id)
        metadata = context.services.get("connection_metadata", {})
        return ConfirmationControlContract(
            environment=str(metadata.get("environment") or "unknown").lower(),
            side_effect_budget=default_confirmation_budget(),
            automation_fingerprint=fingerprint_from_evidence(evidence),
            compensation_plan=default_compensation_plan(order_id),
        )

    def governed_confirmation_cleanup_plan(
        self,
        snapshot: dict,
        control_contract: dict | None = None,
    ) -> dict:
        if control_contract is not None:
            return ConfirmationControlContract.model_validate(
                control_contract
            ).compensation_plan.model_dump(mode="json")
        return default_compensation_plan(snapshot.get("order_id")).model_dump(mode="json")

    def _execute_governed_confirmation(
        self,
        context: ConnectorContext,
        plan: NativeExecutionPlan,
        permit: ExecutionPermit,
    ) -> NativeExecutionResult:
        if not permit.approved or permit.capability != "sales.order.confirm":
            return NativeExecutionResult(
                status="blocked",
                summary="confirmation_permit_invalid",
                errors=["confirmation_requires_valid_permit"],
                safety_flags=ConnectorSafetyFlags(),
            )
        try:
            order_id = int(plan.arguments["order_id"])
            expected_snapshot_hash = str(plan.arguments["expected_state_snapshot_hash"])
            expected_control_contract_hash = str(plan.arguments["expected_control_contract_hash"])
            approved_control_contract = ConfirmationControlContract.model_validate(
                plan.arguments["control_contract"]
            )
        except (KeyError, TypeError, ValueError) as exc:
            return NativeExecutionResult(
                status="blocked",
                summary="invalid_confirmation_arguments",
                errors=[str(exc)],
                safety_flags=ConnectorSafetyFlags(),
            )

        operation = CanonicalOperation(capability=plan.capability, arguments={"order_id": order_id})
        transport = self._write_transport(context)
        before = transport.read_confirmation_snapshot(order_id)
        current_contract = self.governed_confirmation_control_contract(context, operation, before)
        preflight = self.governed_confirmation_preflight(
            context,
            operation,
            before,
            current_contract.model_dump(mode="json"),
        )
        if preflight["status"] != "passed":
            return NativeExecutionResult(
                status="blocked",
                summary="confirmation_preflight_blocked",
                payload={"preflight": preflight, "before": before},
                errors=preflight["issues"],
                safety_flags=ConnectorSafetyFlags(erp_touched=True),
            )
        if (
            current_contract.digest != expected_control_contract_hash
            or approved_control_contract.digest != expected_control_contract_hash
        ):
            return NativeExecutionResult(
                status="blocked",
                summary="confirmation_control_contract_changed_since_approval",
                payload={
                    "before": before,
                    "current_control_contract_hash": current_contract.digest,
                },
                errors=["control_contract_mismatch"],
                safety_flags=ConnectorSafetyFlags(erp_touched=True),
            )
        if stable_json_digest(before) != expected_snapshot_hash:
            return NativeExecutionResult(
                status="blocked",
                summary="confirmation_state_changed_since_approval",
                payload={"before": before},
                errors=["state_snapshot_mismatch"],
                safety_flags=ConnectorSafetyFlags(erp_touched=True),
            )

        transport.confirm_order(order_id)
        after = transport.read_confirmation_snapshot(order_id)
        return NativeExecutionResult(
            status="ok",
            summary="sale_order_confirmed",
            payload={
                "order_id": order_id,
                "before": before,
                "after": after,
                "control_contract": approved_control_contract.model_dump(mode="json"),
            },
            safety_flags=ConnectorSafetyFlags(erp_touched=True, erp_write_performed=True),
        )

    def _execute_declared_field_write(self, context: ConnectorContext, plan: NativeExecutionPlan) -> NativeExecutionResult:
        declared = self._declared_capability(context, plan.capability)
        if declared is None:
            return NativeExecutionResult(
                status="blocked", summary="declared_capability_not_active",
                errors=["declared_capability_not_active"], safety_flags=ConnectorSafetyFlags(),
            )
        if not settings.allow_declared_write_capabilities:
            return NativeExecutionResult(
                status="blocked", summary="declared_write_capabilities_disabled",
                errors=["declared_write_capabilities_disabled"], safety_flags=ConnectorSafetyFlags(),
            )
        if is_denylisted(model=declared.target_model, field=declared.target_field):
            return NativeExecutionResult(
                status="blocked", summary="declared_capability_denylisted",
                errors=["declared_capability_denylisted"], safety_flags=ConnectorSafetyFlags(),
            )
        metadata = context.services.get("connection_metadata", {})
        if str(metadata.get("environment", "")).lower() != "staging":
            return NativeExecutionResult(
                status="blocked", summary="declared_capability_requires_staging_connection",
                errors=["declared_capability_requires_staging_connection"], safety_flags=ConnectorSafetyFlags(),
            )
        try:
            record_id = int(plan.arguments["record_id"])
            value = plan.arguments["value"]
        except (KeyError, TypeError, ValueError) as exc:
            return NativeExecutionResult(
                status="blocked", summary="invalid_declared_capability_arguments",
                errors=[str(exc)], safety_flags=ConnectorSafetyFlags(),
            )
        error = self._validate_declared_value(declared, value)
        if error:
            return NativeExecutionResult(
                status="blocked", summary=error, errors=[error], safety_flags=ConnectorSafetyFlags(),
            )

        transport = self._write_transport(context)
        before = transport.read_field(model=declared.target_model, record_id=record_id, field=declared.target_field)
        transport.write_field(model=declared.target_model, record_id=record_id, field=declared.target_field, value=value)
        return NativeExecutionResult(
            status="ok", summary="declared_field_written",
            payload={
                "model": declared.target_model, "field": declared.target_field,
                "record_id": record_id, "before": before, "written": value,
            },
            safety_flags=ConnectorSafetyFlags(erp_touched=True, erp_write_performed=True),
        )

    def _execute_quote_create_draft(self, context: ConnectorContext, plan: NativeExecutionPlan) -> NativeExecutionResult:
        try:
            partner_id = int(plan.arguments["partner_id"])
            lines = plan.arguments["lines"]
            client_reference = str(plan.arguments["client_reference"])
        except (KeyError, TypeError, ValueError) as exc:
            return NativeExecutionResult(
                status="blocked", summary="invalid_quote_create_draft_arguments",
                errors=[str(exc)], safety_flags=ConnectorSafetyFlags(),
            )

        transport = self._write_transport(context)
        existing_id = transport.find_by_client_reference(client_reference)
        if existing_id is not None:
            # Idempotency: same client_reference -> the existing draft, no
            # second order created.
            return NativeExecutionResult(
                status="ok", summary="draft_already_exists_for_client_reference",
                payload={"order_id": existing_id, "created": False},
                safety_flags=ConnectorSafetyFlags(erp_touched=True, erp_write_performed=False),
            )

        order_id = transport.create_draft(partner_id=partner_id, lines=lines, client_reference=client_reference)
        return NativeExecutionResult(
            status="ok", summary="draft_quote_created",
            payload={"order_id": order_id, "created": True},
            safety_flags=ConnectorSafetyFlags(erp_touched=True, erp_write_performed=True),
        )

    def _execute_pricing_scenario_draft(self, context: ConnectorContext, plan: NativeExecutionPlan) -> NativeExecutionResult:
        try:
            partner_id = int(plan.arguments["partner_id"])
            lines = plan.arguments["lines"]
            client_reference = str(plan.arguments["client_reference"])
            company_id = int(plan.arguments["company_id"])
            pricelist_id = int(plan.arguments["pricelist_id"])
        except (KeyError, TypeError, ValueError) as exc:
            return NativeExecutionResult(
                status="blocked", summary="invalid_pricing_scenario_arguments",
                errors=[str(exc)], safety_flags=ConnectorSafetyFlags(),
            )

        transport = self._write_transport(context)
        existing_id = transport.find_by_client_reference(client_reference)
        if existing_id is not None:
            # Idempotency: same client_reference -> the existing draft, no
            # second order created.
            return NativeExecutionResult(
                status="ok", summary="pricing_scenario_draft_already_exists_for_client_reference",
                payload={"order_id": existing_id, "created": False},
                safety_flags=ConnectorSafetyFlags(erp_touched=True, erp_write_performed=False),
            )

        order_id = transport.create_draft(
            partner_id=partner_id,
            lines=[{"product_id": line["product_id"], "quantity": line["quantity"], "price_unit": line["price_unit"]} for line in lines],
            client_reference=client_reference,
            company_id=company_id,
            pricelist_id=pricelist_id,
        )
        return NativeExecutionResult(
            status="ok", summary="pricing_scenario_draft_created",
            payload={"order_id": order_id, "created": True},
            safety_flags=ConnectorSafetyFlags(erp_touched=True, erp_write_performed=True),
        )

    async def verify_execution(
        self, context: ConnectorContext, operation: CanonicalOperation | str, result: NativeExecutionResult
    ) -> VerificationResult:
        capability = operation if isinstance(operation, str) else operation.capability
        if capability.startswith("declared."):
            return self._verify_declared_field_write(context, result)
        if capability == "sales.order.confirm":
            if result.status not in {"ok", "unknown"} or "after" not in result.payload:
                return VerificationResult(
                    status="not_executed",
                    verified=False,
                    summary="confirmation_not_executed",
                    evidence=result.payload,
                )
            before = result.payload.get("before", {})
            after = result.payload.get("after", {})
            issues: list[str] = []
            contract_payload = result.payload.get("control_contract")
            if not contract_payload:
                issues.append("confirmation_control_contract_missing")
                effect_evaluation = None
            else:
                contract = ConfirmationControlContract.model_validate(contract_payload)
                effect_evaluation = evaluate_confirmation_effects(
                    before,
                    after,
                    contract.side_effect_budget,
                )
                issues.extend(effect_evaluation.violations)
            if int(after.get("order_id") or 0) != int(before.get("order_id") or 0):
                issues.append("order_identity_changed")
            return VerificationResult(
                status="verification_failed" if issues else "verified",
                verified=not issues,
                summary=";".join(issues) if issues else "confirmed_state_and_invoice_boundary_verified",
                evidence={
                    "before": before,
                    "after": after,
                    "generated_picking_ids": [
                        item.get("id")
                        for item in after.get("pickings", [])
                        if item.get("id") not in {entry.get("id") for entry in before.get("pickings", [])}
                    ],
                    "issues": issues,
                    "side_effect_evaluation": (
                        effect_evaluation.model_dump(mode="json")
                        if effect_evaluation is not None
                        else None
                    ),
                },
            )
        if capability == "sales.quote.create_pricing_scenario_draft":
            return self._verify_pricing_scenario_draft(context, operation, result)

        if capability != "quote.create_draft" or result.status != "ok":
            return VerificationResult(status="not_executed", verified=False, summary="no_write_to_verify")

        order_id = result.payload.get("order_id")
        if order_id is None:
            return VerificationResult(status="verification_failed", verified=False, summary="missing_order_id")

        transport = self._write_transport(context)
        order = transport.read_order(int(order_id))
        if order.get("state") != "draft":
            return VerificationResult(
                status="verification_failed", verified=False,
                summary=f"postcondition_failed:expected_state_draft_got_{order.get('state')}",
            )
        return VerificationResult(status="verified", verified=True, summary="draft_state_confirmed")

    def _verify_pricing_scenario_draft(
        self, context: ConnectorContext, operation: CanonicalOperation | str, result: NativeExecutionResult
    ) -> VerificationResult:
        if result.status != "ok":
            return VerificationResult(status="not_executed", verified=False, summary="no_write_to_verify")
        order_id = result.payload.get("order_id")
        if order_id is None:
            return VerificationResult(status="verification_failed", verified=False, summary="missing_order_id")

        expected = operation.arguments if not isinstance(operation, str) else {}
        transport = self._write_transport(context)
        snapshot = transport.read_pricing_scenario_snapshot(int(order_id))

        issues: list[str] = []
        if snapshot.get("state") != "draft":
            issues.append(f"postcondition_failed:expected_state_draft_got_{snapshot.get('state')}")
        if expected.get("partner_id") is not None and snapshot.get("partner_id") != int(expected["partner_id"]):
            issues.append("postcondition_failed:partner_mismatch")
        if expected.get("company_id") is not None and snapshot.get("company_id") != int(expected["company_id"]):
            issues.append("postcondition_failed:company_mismatch")
        if expected.get("pricelist_id") is not None and snapshot.get("pricelist_id") != int(expected["pricelist_id"]):
            issues.append("postcondition_failed:pricelist_mismatch")

        expected_lines = {int(line["product_id"]): line for line in expected.get("lines", [])}
        actual_lines = {int(line["product_id"]): line for line in snapshot.get("lines", []) if line.get("product_id") is not None}
        if set(expected_lines) != set(actual_lines):
            issues.append("postcondition_failed:line_product_set_mismatch")
        else:
            for product_id, expected_line in expected_lines.items():
                actual_line = actual_lines[product_id]
                if float(expected_line["quantity"]) != actual_line["quantity"]:
                    issues.append(f"postcondition_failed:quantity_mismatch:{product_id}")
                expected_price = Decimal(str(expected_line["price_unit"]))
                actual_price = Decimal(str(actual_line["price_unit"]))
                if abs(expected_price - actual_price) > Decimal("0.01"):
                    issues.append(f"postcondition_failed:price_mismatch:{product_id}")
                cost_reference = expected_line.get("cost_reference")
                minimum_margin = expected_line.get("minimum_margin_percent")
                if cost_reference is not None and minimum_margin is not None and actual_price > 0:
                    margin_percent = (actual_price - Decimal(str(cost_reference))) / actual_price * Decimal(100)
                    if margin_percent < Decimal(str(minimum_margin)):
                        issues.append(f"postcondition_failed:margin_floor_violated:{product_id}")

        if snapshot.get("invoice_count", 0) > 0:
            issues.append("forbidden_effect_observed:invoice_created")
        if snapshot.get("picking_count", 0) > 0:
            issues.append("forbidden_effect_observed:picking_created")
        if snapshot.get("purchase_order_count", 0) > 0:
            issues.append("forbidden_effect_observed:purchase_order_created")
        if snapshot.get("manufacturing_order_count", 0) > 0:
            issues.append("forbidden_effect_observed:manufacturing_order_created")

        return VerificationResult(
            status="verification_failed" if issues else "verified",
            verified=not issues,
            summary=";".join(issues) if issues else "pricing_scenario_draft_postconditions_verified",
            evidence={"snapshot": snapshot},
        )

    def _verify_declared_field_write(self, context: ConnectorContext, result: NativeExecutionResult) -> VerificationResult:
        if result.status != "ok":
            return VerificationResult(status="not_executed", verified=False, summary="no_write_to_verify")
        model = result.payload.get("model")
        field = result.payload.get("field")
        record_id = result.payload.get("record_id")
        written = result.payload.get("written")
        if model is None or field is None or record_id is None:
            return VerificationResult(status="verification_failed", verified=False, summary="missing_write_target")
        transport = self._write_transport(context)
        current = transport.read_field(model=model, record_id=int(record_id), field=field)
        verified = current == written
        return VerificationResult(
            status="verified" if verified else "verification_failed",
            verified=verified,
            summary="declared_field_write_confirmed" if verified else "postcondition_failed:read_back_mismatch",
            evidence={"written": written, "read_back": current},
        )

    def execution_permit(self, permit_id: str, capability: str) -> ExecutionPermit:
        return ExecutionPermit(permit_id=permit_id, capability=capability)

    def pull_request(self) -> PullEventsRequest:
        return PullEventsRequest()
