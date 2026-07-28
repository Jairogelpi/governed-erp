from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from sqlalchemy.orm import Session

from erpguard.db.model_packages.candidate import ProcessCandidate
from erpguard.db.model_packages.events import CanonicalEvent, CanonicalObject
from erpguard.domain.processes.candidate_integrity import (
    CandidatePatchError,
    materialize_candidate_definition,
    stable_digest,
)
from erpguard.domain.processes.models import ProcessDefinitionDocument
from erpguard.domain.processes.registry import ProcessRegistry
from erpguard.domain.variants.discovery import VariantDiscoveryService


class CandidateValidationError(ValueError):
    pass


class CandidateNotFound(KeyError):
    pass


class CandidateEvidenceNotFound(CandidateValidationError):
    pass


class CandidateEvidenceNotRelated(CandidateValidationError):
    pass


_OBJECT_TYPE_ALIASES = {
    "sale.order": "sales_order",
    "sale_order": "sales_order",
    "res.partner": "customer",
    "product.product": "product",
}


def _normalize_event_type(value: str) -> str:
    normalized = ".".join(
        part.strip().lower().replace(" ", "_")
        for part in value.split(".")
        if part.strip()
    )
    return {
        "quote.created": "sales.quote.created",
        "quote.reviewed": "sales.quote.reviewed",
        "order.created": "sales.order.created",
    }.get(normalized, normalized)


def _process_event_names(definition: ProcessDefinitionDocument) -> set[str]:
    return {item.name for item in definition.events}


def _process_object_types(definition: ProcessDefinitionDocument) -> set[str]:
    types: set[str] = set()
    for item in definition.objects:
        types.add(item.name)
        types.update(_OBJECT_TYPE_ALIASES.get(value, value) for value in item.external_types)
    return types


def _clean_evidence_refs(evidence_refs: Any) -> list[str]:
    if not isinstance(evidence_refs, list):
        raise CandidateValidationError("evidence_refs_required")
    refs: list[str] = []
    for raw_ref in evidence_refs:
        if not isinstance(raw_ref, str):
            raise CandidateValidationError("invalid_evidence_reference")
        ref = raw_ref.strip()
        prefix, separator, identifier = ref.partition(":")
        if not separator or prefix not in {"evt", "case", "variant"} or not identifier.strip():
            raise CandidateValidationError("invalid_evidence_reference")
        refs.append(f"{prefix}:{identifier.strip()}")
    if not refs:
        raise CandidateValidationError("evidence_refs_required")
    return refs


class CandidateService:
    def __init__(self, session: Session):
        self.session = session

    def _resolve_evidence(
        self,
        *,
        tenant_id: str,
        refs: list[str],
        definition: ProcessDefinitionDocument,
    ) -> None:
        event_names = _process_event_names(definition)
        object_types = _process_object_types(definition)
        variants = VariantDiscoveryService(self.session)

        for ref in refs:
            prefix, identifier = ref.split(":", 1)
            if prefix == "evt":
                row = (
                    self.session.query(CanonicalEvent)
                    .filter(
                        CanonicalEvent.tenant_id == tenant_id,
                        CanonicalEvent.id == identifier,
                    )
                    .one_or_none()
                )
                if row is None:
                    raise CandidateEvidenceNotFound("candidate_evidence_not_found")
                if _normalize_event_type(row.event_type) not in event_names:
                    raise CandidateEvidenceNotRelated("candidate_evidence_not_related_to_base")
                continue

            if prefix == "case":
                object_row = (
                    self.session.query(CanonicalObject)
                    .filter(
                        CanonicalObject.tenant_id == tenant_id,
                        CanonicalObject.object_key == identifier,
                    )
                    .one_or_none()
                )
                if object_row is None:
                    raise CandidateEvidenceNotFound("candidate_evidence_not_found")
                if object_row.object_type not in object_types:
                    raise CandidateEvidenceNotRelated("candidate_evidence_not_related_to_base")
                try:
                    trace = variants.case_trace(
                        tenant_id=tenant_id,
                        case_id=identifier,
                        object_type=object_row.object_type,
                    )
                except KeyError as exc:
                    raise CandidateEvidenceNotFound("candidate_evidence_not_found") from exc
                if not trace.events or any(
                    item.event_type not in event_names for item in trace.events
                ):
                    raise CandidateEvidenceNotRelated("candidate_evidence_not_related_to_base")
                continue

            found_variant = False
            for object_type in sorted(object_types):
                for summary in variants.discover(tenant_id=tenant_id, object_type=object_type):
                    if summary.variant_id != identifier:
                        continue
                    found_variant = True
                    if not summary.sequence or any(
                        event_name not in event_names for event_name in summary.sequence
                    ):
                        raise CandidateEvidenceNotRelated(
                            "candidate_evidence_not_related_to_base"
                        )
                    break
                if found_variant:
                    break
            if not found_variant:
                raise CandidateEvidenceNotFound("candidate_evidence_not_found")

    def create_draft(
        self,
        *,
        tenant_id: str,
        process_key: str,
        base_version: str,
        candidate_version: str,
        changes: dict[str, Any],
        evidence_refs: list[str],
        created_by: str,
        proposal: dict[str, Any] | None = None,
    ) -> ProcessCandidate:
        base_row = ProcessRegistry(self.session).get(process_key, base_version)
        if base_row is None:
            raise CandidateValidationError("base_process_version_not_found")
        if not changes:
            raise CandidateValidationError("candidate_changes_required")
        if proposal is not None and not isinstance(proposal, dict):
            raise CandidateValidationError("invalid_structured_proposal")

        refs = _clean_evidence_refs(evidence_refs)
        try:
            base_definition = ProcessDefinitionDocument.model_validate(
                json.loads(base_row.definition_json)
            )
            candidate_definition, normalized_patch = materialize_candidate_definition(
                base_definition=base_definition.model_dump(mode="json"),
                candidate_version=candidate_version,
                changes=changes,
            )
        except (json.JSONDecodeError, CandidatePatchError) as exc:
            raise CandidateValidationError(str(exc)) from exc

        self._resolve_evidence(tenant_id=tenant_id, refs=refs, definition=base_definition)
        existing = (
            self.session.query(ProcessCandidate)
            .filter_by(
                tenant_id=tenant_id,
                process_key=process_key,
                candidate_version=candidate_version,
            )
            .one_or_none()
        )
        if existing is not None:
            raise CandidateValidationError("candidate_version_exists")

        patch_json = json.dumps(normalized_patch, sort_keys=True, separators=(",", ":"))
        proposal_json = json.dumps(proposal or {}, sort_keys=True, separators=(",", ":"))
        row = ProcessCandidate(
            id=f"candidate_{uuid4().hex}",
            tenant_id=tenant_id,
            process_key=process_key,
            base_version=base_version,
            candidate_version=candidate_version,
            status="draft",
            patch_json=patch_json,
            evidence_json=json.dumps(refs, sort_keys=True, separators=(",", ":")),
            proposal_json=proposal_json,
            base_definition_digest=stable_digest(base_definition),
            patch_digest=stable_digest(normalized_patch),
            candidate_definition_json=json.dumps(
                candidate_definition, sort_keys=True, separators=(",", ":")
            ),
            candidate_definition_digest=stable_digest(candidate_definition),
            validation_status="valid",
            created_by=created_by,
        )
        self.session.add(row)
        self.session.commit()
        self.session.refresh(row)
        return row

    def submit(self, *, tenant_id: str, candidate_id: str) -> ProcessCandidate:
        row = self.get(tenant_id=tenant_id, candidate_id=candidate_id)
        if row.status != "draft":
            raise CandidateValidationError("candidate_not_draft")
        row.status = "submitted"
        row.submitted_at = datetime.now(timezone.utc)
        self.session.commit()
        self.session.refresh(row)
        return row

    def get(self, *, tenant_id: str, candidate_id: str) -> ProcessCandidate:
        row = (
            self.session.query(ProcessCandidate)
            .filter_by(tenant_id=tenant_id, id=candidate_id)
            .one_or_none()
        )
        if row is None:
            raise CandidateNotFound(candidate_id)
        return row
