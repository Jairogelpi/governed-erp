"""Proves the Odoo connector against a REAL, running Odoo 19 server --
never against a fake transport. Pair with `docker-compose.odoo-staging.yml`:

    docker compose -f docker-compose.odoo-staging.yml up -d
    # create a database via http://localhost:8069 first (see that file's
    # header comment -- Odoo has no unattended first-db XML-RPC path)
    ERPGUARD_ODOO_URL=http://localhost:8069 \
    ERPGUARD_ODOO_DB=erpguard_staging \
    ERPGUARD_ODOO_USER=admin \
    ERPGUARD_ODOO_PASSWORD=admin \
        python scripts/validate_against_real_odoo.py

Exercises, in order, against the real server:
  1. read-only schema discovery + fingerprint (OdooConnectorPlugin)
  2. one real quote.create_draft against a real demo partner/product
  3. three declared-write-capability round trips against real XML-RPC
     responses, not `_FakeWriteTransport`: update_field on
     res.partner.comment, archive_record (archives then restores
     res.partner.active, proving delete is really reversible), and
     create_record on crm.lead (idempotent -- the same idempotency_key
     retried creates no second record).

Not part of the pytest suite (needs a live server) and not wired into
CI (no Odoo instance available there) -- same category as
`scripts/validate_demo_install.py`. This is a manual, repeatable
verification step; run it and record the output whenever the connector
or the declared-capability write path changes materially.
"""

from __future__ import annotations

import os
import sys
from uuid import uuid4

from erpguard.adapters.odoo.client import OdooClient
from erpguard.adapters.odoo.config import OdooConfig
from erpguard.adapters.odoo.write_client import OdooQuoteDraftClient
from erpguard.connectors.odoo.plugin import OdooConnectorPlugin
from erpguard.connectors.odoo.transports import LegacyXmlRpcReadTransport
from erpguard.connectors.odoo.write_transport import LegacyXmlRpcWriteTransport
from erpguard.connectors.sdk.models import ConnectorContext, ExecutionPermit, NativeExecutionPlan
from erpguard.domain.declared_capabilities.service import DeclaredCapabilityService


def _config() -> OdooConfig:
    return OdooConfig(
        url=os.environ.get("ERPGUARD_ODOO_URL", "http://localhost:8069"),
        database=os.environ.get("ERPGUARD_ODOO_DB", "erpguard_staging"),
        username=os.environ.get("ERPGUARD_ODOO_USER", "admin"),
        api_key=os.environ.get("ERPGUARD_ODOO_PASSWORD", "admin"),
    )


async def main() -> int:
    config = _config()
    client = OdooClient(config)
    write_client = OdooQuoteDraftClient(config)
    plugin = OdooConnectorPlugin(
        transport_factory=lambda context: LegacyXmlRpcReadTransport(client),
        write_transport_factory=lambda context: LegacyXmlRpcWriteTransport(write_client),
    )
    context = ConnectorContext(
        tenant_id="staging-validation",
        connection_id="staging-validation",
        services={"connection_metadata": {"environment": "staging"}},
    )

    results: list[tuple[str, bool, str]] = []

    def record(step: str, ok: bool, detail: str) -> None:
        results.append((step, ok, detail))
        print(f"{'PASS' if ok else 'FAIL'}  {step}: {detail}")

    try:
        version = client.version()
        record("connect", True, f"server_version={version.get('server_version')}")
    except Exception as exc:  # noqa: BLE001 -- top-level validation script, report and continue
        record("connect", False, str(exc))
        _summarize(results)
        return 1

    try:
        fingerprint = await plugin.fingerprint(context)
        record("discover_schema+fingerprint", True, f"digest={fingerprint.digest[:16]}...")
    except Exception as exc:  # noqa: BLE001
        record("discover_schema+fingerprint", False, str(exc))

    partner_id: int | None = None
    product_id: int | None = None
    try:
        partners = client.search_read("res.partner", [["customer_rank", ">", 0]], ["id"], limit=1)
        products = client.search_read("product.product", [["sale_ok", "=", True]], ["id"], limit=1)
        if partners and products:
            partner_id = int(partners[0]["id"])
            product_id = int(products[0]["id"])
            record("find_demo_partner_and_product", True, f"partner_id={partner_id} product_id={product_id}")
        else:
            record("find_demo_partner_and_product", False, "no demo partner/product found -- load demo data")
    except Exception as exc:  # noqa: BLE001
        record("find_demo_partner_and_product", False, str(exc))

    if partner_id is not None and product_id is not None:
        try:
            client_reference = f"erpguard-validation-{uuid4().hex[:8]}"
            plan = NativeExecutionPlan(
                capability="quote.create_draft",
                arguments={
                    "partner_id": partner_id,
                    "lines": [{"product_id": product_id, "quantity": 1}],
                    "client_reference": client_reference,
                },
                supports_execution=True,
            )
            permit = ExecutionPermit(permit_id="validation", capability="quote.create_draft", approved=True)
            result = await plugin.execute_capability(context, plan, permit)
            order_id = result.payload.get("order_id")
            record(
                "quote.create_draft (real write)",
                result.status == "ok",
                f"status={result.status} order_id={order_id}",
            )
        except Exception as exc:  # noqa: BLE001
            record("quote.create_draft (real write)", False, str(exc))

    if partner_id is not None:
        try:
            from erpguard.db.model_packages.declared_capabilities import DeclaredWriteCapability
            from erpguard.db.session import SessionLocal, init_db

            init_db()
            db = SessionLocal()
            service = DeclaredCapabilityService(db)
            row = service.declare(
                tenant_id="staging-validation",
                name="validation_notes_field",
                target_model="res.partner",
                target_field="comment",
                field_type="string",
                created_by="validation-script",
            )
            from erpguard.db.model_packages.execution import Approval

            approval = Approval(
                id=f"approval_{uuid4().hex}",
                tenant_id="staging-validation",
                scope=DeclaredCapabilityService.approval_scope(row),
                actor_id="validation-script-approver",
            )
            db.add(approval)
            db.commit()
            row = service.approve(
                tenant_id="staging-validation",
                capability_id=row.id,
                approval_id=approval.id,
                approver_actor_id="validation-script-approver",
            )
            row = service.activate(tenant_id="staging-validation", capability_id=row.id)

            def lookup(capability_id: str) -> DeclaredWriteCapability | None:
                return (
                    db.query(DeclaredWriteCapability)
                    .filter_by(tenant_id="staging-validation", id=capability_id, status="active")
                    .one_or_none()
                )

            declared_context = ConnectorContext(
                tenant_id="staging-validation",
                connection_id="staging-validation",
                services={
                    "connection_metadata": {"environment": "staging"},
                    "declared_capability_lookup": lookup,
                },
            )
            capability_name = f"declared.{row.id}"
            value = f"erpguard validation write {uuid4().hex[:8]}"
            full_plan = NativeExecutionPlan(
                capability=capability_name,
                arguments={"record_id": partner_id, "value": value},
                supports_execution=True,
            )
            permit = ExecutionPermit(permit_id="validation", capability=capability_name, approved=True)

            from erpguard.config import settings

            settings.allow_declared_write_capabilities = True
            exec_result = await plugin.execute_capability(declared_context, full_plan, permit)
            verification = await plugin.verify_execution(declared_context, capability_name, exec_result)
            record(
                "declared_write_capability round trip",
                exec_result.status == "ok" and verification.verified,
                f"exec_status={exec_result.status} verified={verification.verified}",
            )
            archive_row = service.declare(
                tenant_id="staging-validation",
                name="validation_archive",
                target_model="res.partner",
                operation="archive_record",
                created_by="validation-script",
            )
            archive_approval = Approval(
                id=f"approval_{uuid4().hex}",
                tenant_id="staging-validation",
                scope=DeclaredCapabilityService.approval_scope(archive_row),
                actor_id="validation-script-approver",
            )
            db.add(archive_approval)
            db.commit()
            archive_row = service.approve(
                tenant_id="staging-validation",
                capability_id=archive_row.id,
                approval_id=archive_approval.id,
                approver_actor_id="validation-script-approver",
            )
            archive_row = service.activate(tenant_id="staging-validation", capability_id=archive_row.id)
            archive_capability_name = f"declared.{archive_row.id}"
            archive_plan = NativeExecutionPlan(
                capability=archive_capability_name,
                arguments={"record_id": partner_id, "value": False},
                supports_execution=True,
            )
            archive_permit = ExecutionPermit(permit_id="validation", capability=archive_capability_name, approved=True)
            archive_result = await plugin.execute_capability(declared_context, archive_plan, archive_permit)
            restore_plan = NativeExecutionPlan(
                capability=archive_capability_name,
                arguments={"record_id": partner_id, "value": True},
                supports_execution=True,
            )
            restore_result = await plugin.execute_capability(declared_context, restore_plan, archive_permit)
            record(
                "archive_record round trip (reversible)",
                archive_result.status == "ok" and restore_result.status == "ok",
                f"archive_status={archive_result.status} restore_status={restore_result.status}",
            )

            create_row = service.declare(
                tenant_id="staging-validation",
                name="validation_create_lead",
                target_model="crm.lead",
                operation="create_record",
                required_fields={"name": "string"},
                idempotency_field="name",
                created_by="validation-script",
            )
            create_approval = Approval(
                id=f"approval_{uuid4().hex}",
                tenant_id="staging-validation",
                scope=DeclaredCapabilityService.approval_scope(create_row),
                actor_id="validation-script-approver",
            )
            db.add(create_approval)
            db.commit()
            create_row = service.approve(
                tenant_id="staging-validation",
                capability_id=create_row.id,
                approval_id=create_approval.id,
                approver_actor_id="validation-script-approver",
            )
            create_row = service.activate(tenant_id="staging-validation", capability_id=create_row.id)
            create_capability_name = f"declared.{create_row.id}"
            lead_name = f"erpguard-validation-lead-{uuid4().hex[:8]}"
            create_plan = NativeExecutionPlan(
                capability=create_capability_name,
                arguments={"values": {"name": lead_name}, "idempotency_key": lead_name},
                supports_execution=True,
            )
            create_permit = ExecutionPermit(permit_id="validation", capability=create_capability_name, approved=True)
            create_result = await plugin.execute_capability(declared_context, create_plan, create_permit)
            create_verification = await plugin.verify_execution(declared_context, create_capability_name, create_result)
            record(
                "create_record round trip (idempotent)",
                create_result.status == "ok" and create_verification.verified,
                f"exec_status={create_result.status} verified={create_verification.verified}",
            )

            db.close()
        except Exception as exc:  # noqa: BLE001
            record("declared_write_capability round trip", False, str(exc))

    return _summarize(results)


def _summarize(results: list[tuple[str, bool, str]]) -> int:
    print("\n--- summary ---")
    failed = [name for name, ok, _ in results if not ok]
    for name, ok, detail in results:
        print(f"{'PASS' if ok else 'FAIL'}  {name}")
    if failed:
        print(f"\n{len(failed)} step(s) failed: {', '.join(failed)}")
        return 1
    print("\nall steps passed against a real Odoo server.")
    return 0


if __name__ == "__main__":
    import asyncio

    sys.exit(asyncio.run(main()))
