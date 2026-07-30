"""Operational feed from persisted canonical events into no-effect shadow evaluation."""

from __future__ import annotations

import json
from collections import defaultdict
from dataclasses import dataclass
from typing import Any
from uuid import uuid4

from sqlalchemy.orm import Session

from erpguard.db.model_packages.event_links import CanonicalEventObject
from erpguard.db.model_packages.events import CanonicalEvent, CanonicalObject
from erpguard.db.model_packages.shadow import ShadowCaseResult, ShadowDeployment, ShadowFeedRun
from erpguard.domain.processes.candidate_integrity import stable_digest
from erpguard.domain.shadow.service import ShadowService, ShadowValidationError
from erpguard.domain.variants.discovery import VariantDiscoveryService


@dataclass(frozen=True)
class FeedProcessingSummary:
    feed_run_id: str
    deployment_id: str
    scanned_case_count: int
    evaluated_case_count: int
    deduplicated_case_count: int
    failed_case_count: int
    failure_codes: tuple[str, ...]
    no_effects: bool = True


@dataclass(frozen=True)
class AutomaticFeedSummary:
    deployment_count: int
    evaluated_case_count: int
    deduplicated_case_count: int
    failed_case_count: int


class OperationalShadowFeedService:
    def __init__(self, session: Session):
        self.session = session
        self.shadow = ShadowService(session)
        self.variants = VariantDiscoveryService(session)

    def _canonical_case_ids(
        self,
        *,
        tenant_id: str,
        object_type: str,
        requested_case_ids: list[str] | None,
    ) -> list[str]:
        query = (
            self.session.query(CanonicalObject.object_key)
            .join(CanonicalEventObject, CanonicalEventObject.object_id == CanonicalObject.id)
            .filter(
                CanonicalObject.tenant_id == tenant_id,
                CanonicalObject.object_type == object_type,
                CanonicalEventObject.tenant_id == tenant_id,
            )
        )
        if requested_case_ids is not None:
            query = query.filter(CanonicalObject.object_key.in_(set(requested_case_ids)))
        return sorted({row[0] for row in query.all()})

    def canonical_case_count(self, *, tenant_id: str, object_type: str) -> int:
        return len(
            self._canonical_case_ids(
                tenant_id=tenant_id,
                object_type=object_type,
                requested_case_ids=None,
            )
        )

    def _projection(
        self,
        *,
        tenant_id: str,
        object_type: str,
        case_id: str,
    ) -> tuple[dict[str, Any], dict[str, Any], str]:
        object_row = (
            self.session.query(CanonicalObject)
            .filter_by(
                tenant_id=tenant_id,
                object_type=object_type,
                object_key=case_id,
            )
            .one_or_none()
        )
        if object_row is None:
            raise KeyError("canonical_case_not_found")
        trace = self.variants.case_trace(
            tenant_id=tenant_id,
            case_id=case_id,
            object_type=object_type,
        )
        event_rows = (
            self.session.query(CanonicalEvent)
            .filter(
                CanonicalEvent.tenant_id == tenant_id,
                CanonicalEvent.event_key.in_([event.event_key for event in trace.events]),
            )
            .all()
        )
        event_by_key = {row.event_key: row for row in event_rows}
        link_rows = (
            self.session.query(CanonicalEventObject)
            .filter(
                CanonicalEventObject.tenant_id == tenant_id,
                CanonicalEventObject.event_id.in_([row.id for row in event_rows]),
            )
            .all()
        )
        links_by_event: dict[str, list[dict[str, str]]] = defaultdict(list)
        for link in link_rows:
            links_by_event[link.event_id].append(
                {"object_id": link.object_id, "qualifier": link.qualifier}
            )
        provenance_events: list[dict[str, Any]] = []
        object_attributes = json.loads(object_row.attributes_json)
        provenance_keys = {
            "correlation_id",
            "historical",
            "synthetic",
            "source_model",
            "source_record_id",
            "source_event_type",
        }
        for trace_event in trace.events:
            row = event_by_key[trace_event.event_key]
            attributes = json.loads(row.attributes_json)
            business_attributes = {
                key: value
                for key, value in attributes.items()
                if key not in provenance_keys
            }
            object_attributes.update(business_attributes)
            provenance_events.append(
                {
                    "event_id": row.id,
                    "event_key": row.event_key,
                    "event_type": trace_event.event_type,
                    "timestamp": row.event_timestamp,
                    "source": row.source,
                    "correlation_id": attributes.get("correlation_id"),
                    "historical": bool(attributes.get("historical", False)),
                    "synthetic": bool(attributes.get("synthetic", False)),
                    "business_attributes_hash": stable_digest(business_attributes),
                    "object_links": sorted(
                        links_by_event[row.id],
                        key=lambda item: (item["object_id"], item["qualifier"]),
                    ),
                }
            )
        provenance = {
            "extraction_mode": "canonical_event_store",
            "object_id": object_row.id,
            "object_key": object_row.object_key,
            "object_type": object_row.object_type,
            "events": provenance_events,
        }
        canonical_trace_hash = stable_digest(
            {
                "case_id": case_id,
                "object_type": object_type,
                "variant_id": trace.variant_id,
                "events": provenance_events,
                "object_attributes": object_attributes,
            }
        )
        return {
            "trace": trace,
            "attributes": object_attributes,
        }, provenance, canonical_trace_hash

    def process_deployment(
        self,
        *,
        tenant_id: str,
        deployment_id: str,
        requested_case_ids: list[str] | None,
        trigger: str,
        created_by: str,
    ) -> FeedProcessingSummary:
        deployment = self.shadow.get_deployment(
            tenant_id=tenant_id,
            deployment_id=deployment_id,
        )
        case_ids = self._canonical_case_ids(
            tenant_id=tenant_id,
            object_type=deployment.object_type,
            requested_case_ids=requested_case_ids,
        )
        evaluated = deduplicated = failed = 0
        failures: list[str] = []
        for case_id in case_ids:
            try:
                projection, provenance, trace_hash = self._projection(
                    tenant_id=tenant_id,
                    object_type=deployment.object_type,
                    case_id=case_id,
                )
                idempotency_key = "canonical:" + stable_digest(
                    {
                        "deployment_id": deployment.id,
                        "case_id": case_id,
                        "canonical_trace_hash": trace_hash,
                    }
                )
                input_hash = stable_digest(
                    {
                        "idempotency_key": idempotency_key,
                        "canonical_trace_hash": trace_hash,
                        "object_attributes": projection["attributes"],
                    }
                )
                existed = (
                    self.session.query(ShadowCaseResult.id)
                    .filter_by(
                        tenant_id=tenant_id,
                        deployment_id=deployment.id,
                        idempotency_key=idempotency_key,
                    )
                    .one_or_none()
                    is not None
                )
                self.shadow.evaluate_trace(
                    tenant_id=tenant_id,
                    deployment_id=deployment.id,
                    trace=projection["trace"],
                    object_attributes=projection["attributes"],
                    idempotency_key=idempotency_key,
                    input_hash=input_hash,
                    evaluation_mode="canonical_feed",
                    canonical_trace_hash=trace_hash,
                    trace_provenance=provenance,
                )
                if existed:
                    deduplicated += 1
                else:
                    evaluated += 1
            except (KeyError, TypeError, ValueError, ShadowValidationError) as exc:
                failed += 1
                failures.append(str(exc.args[0]) if exc.args else type(exc).__name__)
                self.session.rollback()
        run = ShadowFeedRun(
            id=f"shadowfeed_{uuid4().hex}",
            tenant_id=tenant_id,
            deployment_id=deployment.id,
            trigger=trigger,
            requested_case_ids_json=json.dumps(requested_case_ids or [], sort_keys=True),
            scanned_case_count=len(case_ids),
            evaluated_case_count=evaluated,
            deduplicated_case_count=deduplicated,
            failed_case_count=failed,
            failure_codes_json=json.dumps(sorted(failures)),
            no_effects=True,
            created_by=created_by,
        )
        self.session.add(run)
        self.session.commit()
        return FeedProcessingSummary(
            feed_run_id=run.id,
            deployment_id=deployment.id,
            scanned_case_count=len(case_ids),
            evaluated_case_count=evaluated,
            deduplicated_case_count=deduplicated,
            failed_case_count=failed,
            failure_codes=tuple(sorted(failures)),
        )

    def process_applicable_deployments(
        self,
        *,
        tenant_id: str,
        object_keys: list[str],
        created_by: str = "system:canonical-ingestion",
    ) -> AutomaticFeedSummary:
        objects = (
            self.session.query(CanonicalObject)
            .filter(
                CanonicalObject.tenant_id == tenant_id,
                CanonicalObject.object_key.in_(set(object_keys)),
            )
            .all()
        )
        keys_by_type: dict[str, list[str]] = defaultdict(list)
        for row in objects:
            keys_by_type[row.object_type].append(row.object_key)
        deployments = (
            self.session.query(ShadowDeployment)
            .filter_by(tenant_id=tenant_id, status="shadow", no_effects=True)
            .all()
        )
        evaluated = deduplicated = failed = processed = 0
        for deployment in deployments:
            case_ids = keys_by_type.get(deployment.object_type)
            if not case_ids:
                continue
            summary = self.process_deployment(
                tenant_id=tenant_id,
                deployment_id=deployment.id,
                requested_case_ids=case_ids,
                trigger="canonical_ingestion",
                created_by=created_by,
            )
            processed += 1
            evaluated += summary.evaluated_case_count
            deduplicated += summary.deduplicated_case_count
            failed += summary.failed_case_count
        return AutomaticFeedSummary(
            deployment_count=processed,
            evaluated_case_count=evaluated,
            deduplicated_case_count=deduplicated,
            failed_case_count=failed,
        )
