from __future__ import annotations

from dataclasses import dataclass

from erpguard.db.repositories import (
    create_ui_recording_session,
    finish_ui_recording_session,
    get_ui_recording_session,
)
from erpguard.db.session import SessionLocal, init_db


@dataclass(frozen=True)
class UISessionResult:
    session_id: str
    name: str
    description: str | None
    target_base_url: str
    status: str
    created_at: str
    updated_at: str


class UIRecordingSessionService:
    def create_session(self, name: str, description: str | None, target_base_url: str) -> UISessionResult:
        init_db()
        db = SessionLocal()
        try:
            row = create_ui_recording_session(
                db,
                name=name,
                description=description,
                target_base_url=target_base_url,
            )
            return self._to_result(row)
        finally:
            db.close()

    def get_session(self, session_id: str) -> UISessionResult | None:
        init_db()
        db = SessionLocal()
        try:
            row = get_ui_recording_session(db, session_id)
            if row is None:
                return None
            return self._to_result(row)
        finally:
            db.close()

    def finish_session(self, session_id: str) -> UISessionResult | None:
        init_db()
        db = SessionLocal()
        try:
            row = finish_ui_recording_session(db, session_id)
            if row is None:
                return None
            return self._to_result(row)
        finally:
            db.close()

    def _to_result(self, row) -> UISessionResult:
        return UISessionResult(
            session_id=row.id,
            name=row.name,
            description=row.description,
            target_base_url=row.target_base_url,
            status=row.status,
            created_at=row.created_at.isoformat(),
            updated_at=row.updated_at.isoformat(),
        )
