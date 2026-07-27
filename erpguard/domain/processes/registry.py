from __future__ import annotations

import hashlib
import json

from sqlalchemy.orm import Session

from erpguard.db.model_packages.process import ProcessDefinition
from erpguard.domain.processes.validation import load_process_yaml


class ProcessDefinitionConflict(ValueError):
    pass


class ProcessRegistry:
    def __init__(self, session: Session):
        self.session = session

    def register_yaml(self, text: str) -> ProcessDefinition:
        definition = load_process_yaml(text)
        payload = definition.model_dump(mode="json")
        serialized = json.dumps(payload, sort_keys=True, separators=(",", ":"))
        existing = (
            self.session.query(ProcessDefinition)
            .filter_by(process_key=definition.process_key, version=definition.version)
            .one_or_none()
        )
        if existing is not None:
            existing_payload = json.loads(existing.definition_json)
            if existing_payload == payload:
                return existing
            raise ProcessDefinitionConflict("process_version_immutable")
        row = ProcessDefinition(
            id=f"process_{hashlib.sha256(f'{definition.process_key}:{definition.version}'.encode()).hexdigest()[:24]}",
            process_key=definition.process_key,
            version=definition.version,
            definition_json=serialized,
        )
        self.session.add(row)
        self.session.commit()
        self.session.refresh(row)
        return row

    def get(self, process_key: str, version: str) -> ProcessDefinition | None:
        return (
            self.session.query(ProcessDefinition)
            .filter_by(process_key=process_key, version=version)
            .one_or_none()
        )

    def diff(self, process_key: str, from_version: str, to_version: str) -> dict:
        before = self.get(process_key, from_version)
        after = self.get(process_key, to_version)
        if before is None or after is None:
            raise KeyError("process_version_not_found")
        before_payload = json.loads(before.definition_json)
        after_payload = json.loads(after.definition_json)
        changed = sorted(
            key for key in set(before_payload) | set(after_payload)
            if before_payload.get(key) != after_payload.get(key)
        )
        return {
            "process_key": process_key,
            "from_version": from_version,
            "to_version": to_version,
            "changed": bool(changed),
            "changed_sections": changed,
        }
