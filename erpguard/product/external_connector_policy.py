from __future__ import annotations

from dataclasses import dataclass, field


_ALLOWED_OPERATIONS: dict[str, set[str]] = {
    "google_calendar_readonly": {
        "test_readiness",
        "read_calendars",
        "read_upcoming_events",
    }
}

_FORBIDDEN_OPERATIONS: set[str] = {
    "create_event",
    "update_event",
    "delete_event",
    "send_email",
    "read_email_body",
    "read_drive_content",
    "send_whatsapp",
    "mcp_execute",
    "arbitrary_http",
    "erp_write",
}

_ALLOWED_SCOPES: dict[str, list[str]] = {
    "google_calendar_readonly": [
        "https://www.googleapis.com/auth/calendar.readonly",
    ]
}


@dataclass
class PolicyCheckResult:
    allowed: bool
    connector_id: str
    operation: str
    violations: list[str] = field(default_factory=list)
    allowed_scopes: list[str] = field(default_factory=list)
    policy_version: str = "sprint18-v1"


class ExternalConnectorPolicy:
    def check(self, connector_id: str, operation: str) -> PolicyCheckResult:
        violations: list[str] = []

        if operation in _FORBIDDEN_OPERATIONS:
            violations.append(f"operation '{operation}' is explicitly forbidden")

        allowed_ops = _ALLOWED_OPERATIONS.get(connector_id, set())
        if operation not in allowed_ops and operation not in _FORBIDDEN_OPERATIONS:
            violations.append(
                f"operation '{operation}' is not in the allowed set for '{connector_id}'"
            )

        return PolicyCheckResult(
            allowed=len(violations) == 0,
            connector_id=connector_id,
            operation=operation,
            violations=violations,
            allowed_scopes=_ALLOWED_SCOPES.get(connector_id, []),
        )

    def get_connector_policy(self, connector_id: str) -> dict:
        return {
            "connector_id": connector_id,
            "allowed_operations": sorted(_ALLOWED_OPERATIONS.get(connector_id, set())),
            "forbidden_operations": sorted(_FORBIDDEN_OPERATIONS),
            "allowed_scopes": _ALLOWED_SCOPES.get(connector_id, []),
            "write_operations_enabled": False,
            "mcp_execution_enabled": False,
            "arbitrary_http_enabled": False,
            "erp_write_enabled": False,
            "policy_version": "sprint18-v1",
        }

    def list_connectors(self) -> list[dict]:
        return [
            {
                "connector_id": cid,
                "status": "pilot",
                "allowed_operations": sorted(ops),
                "allowed_scopes": _ALLOWED_SCOPES.get(cid, []),
                "fixture_mode_default": True,
                "real_read_flag": "USE_REAL_GOOGLE_CALENDAR",
                "write_operations_enabled": False,
            }
            for cid, ops in _ALLOWED_OPERATIONS.items()
        ]
