"""Audit tests for Sprint 79 - Odoo read-only demo flow."""

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from erpguard.db.models import Base
from erpguard.product.odoo_read_only_demo_flow import (
    OdooReadOnlyDemoAuditService,
    OdooReadOnlyDemoFlowInput,
)
from test_odoo_read_only_adapter_shell import _activation
from test_odoo_read_only_demo_flow import _service


def test_audit_records_completed_flow_and_no_raw_secret():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    db = Session()
    activation = _activation(db, secret="demo-flow-secret")

    _service(db).run_flow(
        OdooReadOnlyDemoFlowInput(
            activation_id=activation.activation_id,
            allow_network_test=True,
            allow_business_read=True,
        )
    )

    events = OdooReadOnlyDemoAuditService(db).get_audit().events
    payload = str(events).lower()

    assert any(event["event_type"] == "odoo_read_only_demo_flow_completed" for event in events)
    assert "demo-flow-secret" not in payload
    assert "password" not in payload
    assert "api_key" not in payload
    assert "token" not in payload
    assert "secret" not in payload
