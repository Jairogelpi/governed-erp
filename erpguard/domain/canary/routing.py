"""Spec 92 Sec 9.3 -- deterministic canary bucket assignment.

No randomness, no LLM, no global RNG: the bucket is a pure hash of the
routing identity. Same inputs always produce the same bucket; changing a
policy's percentage doesn't reshuffle who's already routed where.
"""

from __future__ import annotations

from erpguard.domain.processes.candidate_integrity import stable_digest

BUCKET_MODULUS = 10000


def compute_bucket(*, tenant_id: str, canary_policy_id: str, process_key: str, business_object_key: str) -> int:
    digest = stable_digest(f"{tenant_id}:{canary_policy_id}:{process_key}:{business_object_key}")
    return int(digest, 16) % BUCKET_MODULUS


def select_lane(*, bucket: int, percentage_basis_points: int) -> str:
    return "canary" if bucket < percentage_basis_points else "stable"
