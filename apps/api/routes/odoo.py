from __future__ import annotations

import json
from xmlrpc.client import Fault

from fastapi import APIRouter, Response
from fastapi.responses import JSONResponse

from apps.api.schemas.odoo import (
    OdooConnectionCreateRequest,
    OdooConnectionCreateResponse,
    OdooConnectionTestResponse,
    OdooDiagnosisRequest,
    OdooDiagnosisResponse,
    OdooRawSalesOrderLine,
    OdooRawSalesOrderSummaryOrder,
    OdooRawSalesOrderSummaryResponse,
)
from erpguard.adapters.odoo.config import OdooConfig
from erpguard.adapters.odoo.diagnosis import OdooDiagnosisService
from erpguard.adapters.odoo.readonly_client import build_readonly_client
from erpguard.canonical.enums import ERPType
from erpguard.db.repositories import create_audit_event, create_connection, get_connection
from erpguard.db.session import SessionLocal, init_db

router = APIRouter(prefix="/v1/odoo", tags=["odoo"])


@router.post("/connections", response_model=OdooConnectionCreateResponse)
def create_odoo_connection(request: OdooConnectionCreateRequest, response: Response):
    _mark_deprecated(response)
    init_db()
    session = SessionLocal()
    try:
        config = _request_to_config(request)
        connection = create_connection(session, request.name, ERPType.ODOO, config.model_dump())
        create_audit_event(
            session,
            connection.id,
            "odoo_connection_created",
            {
                "event": "odoo_connection_created",
                "connection_id": connection.id,
                "erp_type": connection.erp_type,
                "secrets_redacted": True,
            },
        )
        return OdooConnectionCreateResponse(
            connection_id=connection.id,
            name=connection.name,
            erp_type=connection.erp_type,
            status=connection.status,
            secrets_redacted=True,
        )
    finally:
        session.close()


@router.post("/connections/{connection_id}/test", response_model=OdooConnectionTestResponse)
def test_odoo_connection(connection_id: str, response: Response):
    _mark_deprecated(response)
    init_db()
    session = SessionLocal()
    try:
        connection = _get_odoo_connection(session, connection_id)
        if connection is None:
            return _not_found("odoo_connection_not_found", f"Odoo connection '{connection_id}' not found.")
        config = _connection_config(connection)
        client = build_readonly_client(config)
        try:
            version = client.version()
            uid = client.authenticate()
        except Exception as exc:  # fail closed for connection/auth issues
            return _controlled_connection_error("odoo_authentication_failed", "Odoo authentication failed.", connection_id, exc)
        return OdooConnectionTestResponse(
            connection_id=connection.id,
            status="ok",
            erp_type=connection.erp_type,
            server_version=version.get("server_version"),
            uid=uid,
            read_only_mode=True,
            secrets_redacted=True,
        )
    finally:
        session.close()


@router.post("/connections/{connection_id}/diagnose", response_model=OdooDiagnosisResponse)
def diagnose_odoo_connection(connection_id: str, request: OdooDiagnosisRequest, response: Response):
    _mark_deprecated(response)
    init_db()
    session = SessionLocal()
    try:
        connection = _get_odoo_connection(session, connection_id)
        if connection is None:
            return _not_found("odoo_connection_not_found", f"Odoo connection '{connection_id}' not found.")
        config = _connection_config(connection)
        client = build_readonly_client(config)
        service = OdooDiagnosisService(client=client, config=config)
        try:
            result = service.run(include_samples=request.include_samples, sample_limits=request.sample_limits.model_dump())
        except (Fault, TimeoutError, ConnectionError, OSError) as exc:
            return _controlled_connection_error(
                "odoo_connection_error",
                "Could not complete read-only Odoo diagnosis.",
                connection_id,
                exc,
                status_code=503,
            )
        create_audit_event(
            session,
            connection.id,
            "odoo_diagnosis_completed",
            {
                "event": "odoo_diagnosis_completed",
                "connection_id": connection.id,
                "read_only_mode": True,
                "status": result.get("status"),
                "warnings": result.get("warnings", []),
            },
        )
        result["connection_id"] = connection.id
        result["secrets_redacted"] = True
        return OdooDiagnosisResponse.model_validate(result)
    finally:
        session.close()


@router.get("/connections/{connection_id}/sales-orders/{order_reference}/raw-summary", response_model=OdooRawSalesOrderSummaryResponse)
def read_sales_order_raw_summary(connection_id: str, order_reference: str):
    init_db()
    session = SessionLocal()
    try:
        connection = _get_odoo_connection(session, connection_id)
        if connection is None:
            return _not_found("odoo_connection_not_found", f"Odoo connection '{connection_id}' not found.")
        config = _connection_config(connection)
        client = build_readonly_client(config)
        try:
            orders = client.search_read(
                "sale.order",
                [["name", "=", order_reference]],
                ["id", "name", "state", "partner_id", "amount_total", "order_line"],
                limit=1,
            )
            if not orders:
                return _not_found(
                    "odoo_sales_order_not_found",
                    f"Sales order '{order_reference}' not found.",
                    connection_id=connection_id,
                )
            order_payload = orders[0]
            line_ids = [int(line_id) for line_id in order_payload.get("order_line", [])]
            line_rows = client.search_read(
                "sale.order.line",
                [["id", "in", line_ids]],
                ["id", "product_id", "product_uom_qty", "price_unit"],
            )
        except (Fault, TimeoutError, ConnectionError, OSError) as exc:
            return _controlled_connection_error(
                "odoo_connection_error",
                "Could not complete read-only Odoo diagnosis.",
                connection_id,
                exc,
                status_code=503,
            )

        order = OdooRawSalesOrderSummaryOrder(
            id=order_payload.get("id"),
            name=order_payload.get("name"),
            state=order_payload.get("state"),
            partner=_many2one_name(order_payload.get("partner_id")),
            amount_total=order_payload.get("amount_total"),
            line_count=len(order_payload.get("order_line", [])),
        )
        lines = [
            OdooRawSalesOrderLine(
                id=row.get("id"),
                product_id=_many2one_id(row.get("product_id")),
                product_name=_many2one_name(row.get("product_id")),
                quantity=row.get("product_uom_qty"),
                price_unit=row.get("price_unit"),
            )
            for row in line_rows
        ]
        create_audit_event(
            session,
            connection.id,
            "odoo_raw_sales_order_summary_read",
            {
                "event": "odoo_raw_sales_order_summary_read",
                "connection_id": connection.id,
                "order_reference": order_reference,
                "line_count": len(lines),
            },
        )
        return OdooRawSalesOrderSummaryResponse(
            connection_id=connection.id,
            order_reference=order_reference,
            status="found",
            read_only_mode=True,
            order=order,
            lines=lines,
            secrets_redacted=True,
        )
    finally:
        session.close()


def _request_to_config(request: OdooConnectionCreateRequest) -> OdooConfig:
    payload = request.model_dump(exclude_none=True)
    payload["field_mappings"] = request.field_mappings.model_dump(exclude_none=True) if request.field_mappings else {}
    return OdooConfig.model_validate(payload)


def _connection_config(connection) -> OdooConfig:
    config_json = json.loads(connection.config_json)
    return OdooConfig.model_validate(config_json)


def _get_odoo_connection(session, connection_id: str):
    connection = get_connection(session, connection_id)
    if connection is None or connection.erp_type != ERPType.ODOO.value:
        return None
    return connection


def _not_found(code: str, message: str, connection_id: str | None = None):
    details = {}
    if connection_id is not None:
        details["connection_id"] = connection_id
    return JSONResponse(
        status_code=404,
        content={"error": {"code": code, "message": message, "details": details}},
    )


def _controlled_connection_error(
    code: str,
    message: str,
    connection_id: str,
    exc: Exception,
    status_code: int = 400,
):
    return JSONResponse(
        status_code=status_code,
        content={
            "error": {
                "code": code,
                "message": message,
                "details": {
                    "connection_id": connection_id,
                    "error_type": type(exc).__name__,
                },
            }
        },
    )


def _many2one_id(value):
    if isinstance(value, (list, tuple)) and value:
        return value[0]
    return value


def _many2one_name(value):
    if isinstance(value, (list, tuple)) and len(value) >= 2:
        return value[1]
    return None


def _mark_deprecated(response: Response) -> None:
    response.headers["Deprecation"] = "true"
    response.headers["Link"] = '</v1/unified/connections>; rel="successor-version"'
