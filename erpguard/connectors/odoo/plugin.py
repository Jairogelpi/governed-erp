from __future__ import annotations

from collections.abc import Callable

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

    async def test_connection(self, context: ConnectorContext) -> ConnectionTestResult:
        transport = self._transport(context)
        version = transport.version()
        transport.authenticate()
        return ConnectionTestResult(status="ok", summary=f"odoo_read_only:{version.get('server_version', 'unknown')}")

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
        else:
            steps = ["odoo_create_draft_quote"]
        return NativeExecutionPlan(
            capability=capability, status="planned", steps=steps,
            supports_execution=definition.supports_execution, arguments=arguments,
        )

    async def execute_capability(
        self, context: ConnectorContext, plan: NativeExecutionPlan, permit: ExecutionPermit
    ) -> NativeExecutionResult:
        if plan.capability == "sales.order.confirm":
            return self._execute_governed_confirmation(context, plan, permit)
        if plan.capability != "quote.create_draft":
            return NativeExecutionResult(
                status="blocked", summary="odoo_connector_v2_is_read_only",
                errors=["write_capability_not_declared"], safety_flags=ConnectorSafetyFlags(),
            )
        return self._execute_quote_create_draft(context, plan)

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

    async def verify_execution(
        self, context: ConnectorContext, operation: CanonicalOperation | str, result: NativeExecutionResult
    ) -> VerificationResult:
        capability = operation if isinstance(operation, str) else operation.capability
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

    def execution_permit(self, permit_id: str, capability: str) -> ExecutionPermit:
        return ExecutionPermit(permit_id=permit_id, capability=capability)

    def pull_request(self) -> PullEventsRequest:
        return PullEventsRequest()
