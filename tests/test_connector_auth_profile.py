from __future__ import annotations

from erpguard.db.session import SessionLocal, init_db
from erpguard.product.connector_auth_profile import ConnectorAuthProfileService


def test_connector_auth_profile_lifecycle_redacts_secrets_and_records_audit():
    init_db()
    session = SessionLocal()
    try:
        service = ConnectorAuthProfileService(session)
        created = service.create_profile(
            connector_id="gmail",
            display_name="Gmail readiness",
            auth_type="oauth_placeholder",
            requested_scopes=["gmail.readonly"],
            credential={"access_token": "gmail_secret_token"},
            created_by={"type": "user", "id": "operator"},
        )

        assert created.status == "active"
        assert created.oauth_ready is False
        assert created.oauth_flow_enabled is False
        assert created.provider_api_calls_enabled is False
        assert created.secret_redacted is True
        assert "gmail_secret_token" not in created.model_dump_json()

        test_result = service.simulate_test(created.profile_id, actor={"id": "operator"})
        assert test_result.test_status == "simulated_passed"
        assert test_result.provider_api_called is False
        assert test_result.secret_redacted is True

        rotated = service.rotate(created.profile_id, credential={"access_token": "rotated_secret"}, actor={"id": "operator"})
        assert rotated.status == "rotated"
        assert rotated.credential_ref != created.credential_ref
        assert "rotated_secret" not in rotated.model_dump_json()

        revoked = service.revoke(created.profile_id, actor={"id": "operator"})
        assert revoked.status == "revoked"

        audit = service.audit(created.profile_id)
        assert [event.event_type for event in audit] == [
            "profile_created",
            "simulated_connection_test",
            "credential_rotated",
            "credential_revoked",
        ]
        assert "gmail_secret_token" not in "".join(event.model_dump_json() for event in audit)
        assert "rotated_secret" not in "".join(event.model_dump_json() for event in audit)
    finally:
        session.close()
