from __future__ import annotations

import json

from erpguard.core.errors import ObjectNotFoundError
from erpguard.db.repositories import (
    create_audit_export,
    create_platform_audit_event,
    get_audit_export,
    get_tenant,
)
from erpguard.product.models import AuditExportModel
from erpguard.product.platform_secret_redactor import SecretRedactionService

_AUDIT_EXPORT_ENABLED = True


class AuditExportService:
    def __init__(self, session) -> None:
        self.session = session
        self._redactor = SecretRedactionService()

    def generate(self, tenant_id: str, filters: dict | None = None) -> AuditExportModel:
        if not _AUDIT_EXPORT_ENABLED:
            raise ValueError("AUDIT_EXPORT_ENABLED=false — audit export is disabled.")

        tenant_row = get_tenant(self.session, tenant_id)
        if tenant_row is None:
            raise ObjectNotFoundError(f"Tenant '{tenant_id}' not found.")

        filters = filters or {}
        records = self._collect_records(filters)
        redacted = [self._redactor.redact(r) for r in records]

        row = create_audit_export(
            session=self.session,
            tenant_id=tenant_id,
            export_type="json",
            filters_json=json.dumps(filters),
            record_count=len(redacted),
            result_json=json.dumps(redacted),
        )

        create_platform_audit_event(
            session=self.session,
            tenant_id=tenant_id,
            event_category="export",
            event_type="audit_export.generated",
            actor_json=json.dumps({"type": "system", "id": "platform"}),
            details_json=json.dumps({"export_id": row.id, "record_count": len(redacted)}),
            severity="info",
        )

        return self._row_to_model(row, redacted)

    def get(self, export_id: str) -> AuditExportModel:
        row = get_audit_export(self.session, export_id)
        if row is None:
            raise ObjectNotFoundError(f"Audit export '{export_id}' not found.")
        result = json.loads(row.result_json)
        return self._row_to_model(row, result)

    def _collect_records(self, filters: dict) -> list[dict]:
        from erpguard.db.models import WritePilotEvidence, WritePilotRun, PlatformAuditEvent

        records = []
        for ev in self.session.query(WritePilotEvidence).limit(200).all():
            records.append({
                "record_type": "write_pilot_evidence",
                "id": ev.id,
                "run_id": ev.run_id,
                "skill_id": ev.skill_id,
                "action_taken": ev.action_taken,
                "target_model": ev.target_model,
                "allow_r1_real_write_pilot": ev.allow_r1_real_write_pilot,
                "allow_generic_real_odoo_writes": False,
                "created_at": ev.created_at.isoformat(),
            })

        for run in self.session.query(WritePilotRun).limit(200).all():
            records.append({
                "record_type": "write_pilot_run",
                "id": run.id,
                "skill_id": run.skill_id,
                "status": run.status,
                "executed_action": run.executed_action,
                "allow_r1_real_write_pilot": run.allow_r1_real_write_pilot,
                "allow_generic_real_odoo_writes": False,
                "created_at": run.created_at.isoformat(),
            })

        for pae in self.session.query(PlatformAuditEvent).limit(200).all():
            records.append({
                "record_type": "platform_audit_event",
                "id": pae.id,
                "tenant_id": pae.tenant_id,
                "event_category": pae.event_category,
                "event_type": pae.event_type,
                "severity": pae.severity,
                "created_at": pae.created_at.isoformat(),
            })

        return records

    @staticmethod
    def _row_to_model(row, result: list) -> AuditExportModel:
        return AuditExportModel(
            export_id=row.id,
            tenant_id=row.tenant_id,
            export_type=row.export_type,
            filters=json.loads(row.filters_json),
            record_count=row.record_count,
            status=row.status,
            result=result,
            created_at=row.created_at.isoformat(),
            completed_at=row.completed_at.isoformat() if row.completed_at else None,
        )
