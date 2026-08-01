"""Spec 92 Workstream D: one sealed, verifiable evidence object connecting
the complete decision-to-outcome lifecycle (Sec 11).

Pure functions only -- gathering the referenced rows, deciding what is
missing, and persisting the bundle happens in
`erpguard.application.evidence.decision_outcome_service`. Keeping the
hashing/labeling/secret-scan rules here means they stay reproducible from
inputs alone, same idiom as `erpguard.domain.canary.routing`.
"""

from __future__ import annotations

from typing import Any

from erpguard.domain.processes.candidate_integrity import stable_digest

REALITY_LABELS = {"live", "staging_live", "fixture", "synthetic", "derived", "manual"}

# Matched case-insensitively against dict *keys* only -- scanning values would
# false-positive on ordinary business text ("customer secret preferences").
_SECRET_KEY_MARKERS = (
    "secret", "credential", "password", "api_key", "apikey", "token",
    "private_key", "access_key",
)


class InvalidRealityLabel(ValueError):
    pass


class ResourceReference:
    """One manifest entry (Spec 92 Sec 11.2): a resource type/id pinned to
    the content hash it had when referenced, plus its reality label."""

    __slots__ = ("resource_type", "resource_id", "content_hash", "created_at", "tenant_id", "reality_label")

    def __init__(
        self,
        *,
        resource_type: str,
        resource_id: str,
        content_hash: str,
        created_at: str,
        tenant_id: str,
        reality_label: str,
    ) -> None:
        if reality_label not in REALITY_LABELS:
            raise InvalidRealityLabel(reality_label)
        self.resource_type = resource_type
        self.resource_id = resource_id
        self.content_hash = content_hash
        self.created_at = created_at
        self.tenant_id = tenant_id
        self.reality_label = reality_label

    def as_dict(self) -> dict[str, Any]:
        return {
            "resource_type": self.resource_type,
            "resource_id": self.resource_id,
            "content_hash": self.content_hash,
            "created_at": self.created_at,
            "tenant_id": self.tenant_id,
            "reality_label": self.reality_label,
        }


def _ordered(references: list[ResourceReference]) -> list[dict[str, Any]]:
    # Creation-time first (a lifecycle's natural order), resource_type/id as
    # the tiebreak -- deterministic regardless of the order the application
    # service happened to gather rows in.
    return sorted(
        (ref.as_dict() for ref in references),
        key=lambda item: (item["created_at"], item["resource_type"], item["resource_id"]),
    )


def manifest_hash(references: list[ResourceReference]) -> str:
    return stable_digest(_ordered(references))


def chain_hash(references: list[ResourceReference]) -> str:
    """Binds the ORDERED resource hashes (Sec 11.4): each link folds the
    previous chain value into the next resource's hash, so altering or
    reordering any single reference changes every link after it."""

    chain = ""
    for entry in _ordered(references):
        chain = stable_digest({"previous": chain, "resource": entry})
    return chain


def content_hash(references: list[ResourceReference], *, recommendation_id: str, measurement_plan_id: str | None) -> str:
    return stable_digest(
        {
            "recommendation_id": recommendation_id,
            "measurement_plan_id": measurement_plan_id,
            "references": _ordered(references),
        }
    )


def contains_secret_like_field(payload: Any) -> bool:
    """Sec 11.4/11.5: no raw credential, API key, or secret reference may
    enter the exported payload. This is a defense-in-depth scan over the
    manifest/export payload -- the actual secret vault is never referenced
    by id in any of the gathered rows to begin with."""

    if isinstance(payload, dict):
        for key, value in payload.items():
            if isinstance(key, str) and any(marker in key.lower() for marker in _SECRET_KEY_MARKERS):
                return True
            if contains_secret_like_field(value):
                return True
        return False
    if isinstance(payload, list):
        return any(contains_secret_like_field(item) for item in payload)
    return False
