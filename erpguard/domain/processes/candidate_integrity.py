"""Deterministic, bounded process-candidate patching.

Candidate patches are deliberately small and typed.  They produce a complete
process definition before a candidate is persisted, which gives later replay
work a stable artifact rather than an arbitrary client dictionary.
"""

from __future__ import annotations

import hashlib
import json
from typing import Any

from pydantic import BaseModel, ValidationError

from erpguard.domain.processes.models import (
    ProcessDecision,
    ProcessDefinitionDocument,
    ProcessEvent,
    ProcessMetric,
    ProcessPolicy,
)
from erpguard.domain.processes.validation import ProcessValidationError, validate_process_definition


class CandidatePatchError(ValueError):
    """Raised when a candidate patch is not part of the safe patch contract."""


ALLOWED_PATCH_OPERATIONS = frozenset(
    {
        "add_event",
        "remove_event",
        "add_decision",
        "modify_decision",
        "add_policy",
        "modify_policy",
        "add_metric",
        "modify_metric",
    }
)
BLOCKED_PATCH_OPERATIONS = frozenset(
    {
        "arbitrary_code",
        "raw_adapter_call",
        "raw_odoo_method",
        "unregistered_capability",
        "removing_mandatory_policy",
    }
)

_SECTION_MODEL_BY_OPERATION: dict[str, type[BaseModel]] = {
    "add_event": ProcessEvent,
    "add_decision": ProcessDecision,
    "modify_decision": ProcessDecision,
    "add_policy": ProcessPolicy,
    "modify_policy": ProcessPolicy,
    "add_metric": ProcessMetric,
    "modify_metric": ProcessMetric,
}
_SECTION_BY_OPERATION = {
    "add_event": "events",
    "add_decision": "decisions",
    "modify_decision": "decisions",
    "add_policy": "policies",
    "modify_policy": "policies",
    "add_metric": "metrics",
    "modify_metric": "metrics",
}


def stable_digest(value: Any) -> str:
    """Return a digest independent of JSON object key ordering."""

    if isinstance(value, BaseModel):
        value = value.model_dump(mode="json")
    serialized = json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


def _invalid_patch() -> CandidatePatchError:
    return CandidatePatchError("invalid_candidate_patch")


def normalize_patch(changes: Any) -> list[dict[str, Any]]:
    """Normalize the supported shorthand and explicit operation-list forms."""

    if not isinstance(changes, dict) or not changes:
        raise _invalid_patch()

    if "operations" in changes:
        if set(changes) != {"operations"} or not isinstance(changes["operations"], list):
            raise _invalid_patch()
        raw_operations = changes["operations"]
        operations: list[dict[str, Any]] = []
        for raw in raw_operations:
            if not isinstance(raw, dict) or set(raw) != {"op", "value"}:
                raise _invalid_patch()
            operations.append({"op": raw["op"], "value": raw["value"]})
    else:
        operations = [
            {"op": operation, "value": value}
            for operation, value in sorted(changes.items(), key=lambda item: str(item[0]))
        ]

    if not operations:
        raise _invalid_patch()
    for operation in operations:
        name = operation["op"]
        if not isinstance(name, str) or not name:
            raise _invalid_patch()
        if name in BLOCKED_PATCH_OPERATIONS:
            raise CandidatePatchError("invalid_candidate_patch:blocked_candidate_operation")
        if name not in ALLOWED_PATCH_OPERATIONS:
            raise CandidatePatchError("unsupported_candidate_operation")
    return operations


def _validate_operation_value(operation: str, value: Any) -> dict[str, Any] | str:
    if operation == "remove_event":
        if not isinstance(value, str) or not value.strip():
            raise _invalid_patch()
        return value.strip()
    model = _SECTION_MODEL_BY_OPERATION[operation]
    try:
        return model.model_validate(value).model_dump(mode="json")
    except (ValidationError, TypeError, ValueError) as exc:
        raise _invalid_patch() from exc


def _replace_named_item(items: list[dict[str, Any]], value: dict[str, Any]) -> None:
    name = value["name"]
    for index, current in enumerate(items):
        if current.get("name") == name:
            items[index] = value
            return
    raise _invalid_patch()


def _append_named_item(items: list[dict[str, Any]], value: dict[str, Any]) -> None:
    if any(current.get("name") == value["name"] for current in items):
        raise _invalid_patch()
    items.append(value)


def materialize_candidate_definition(
    *,
    base_definition: dict[str, Any],
    candidate_version: str,
    changes: Any,
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Apply and validate a bounded patch against one immutable base document."""

    try:
        base = validate_process_definition(ProcessDefinitionDocument.model_validate(base_definition))
    except (ValidationError, ProcessValidationError, TypeError, ValueError) as exc:
        raise CandidatePatchError("invalid_base_process_definition") from exc

    if candidate_version == base.version:
        raise CandidatePatchError("candidate_version_must_differ_from_base")

    operations = normalize_patch(changes)
    candidate = base.model_dump(mode="json")
    candidate["version"] = candidate_version

    for operation in operations:
        name = operation["op"]
        value = _validate_operation_value(name, operation["value"])
        if name == "remove_event":
            events = candidate["events"]
            before = len(events)
            candidate["events"] = [item for item in events if item["name"] != value]
            if len(candidate["events"]) == before:
                raise _invalid_patch()
            continue
        section = candidate[_SECTION_BY_OPERATION[name]]
        if name.startswith("add_"):
            _append_named_item(section, value)  # type: ignore[arg-type]
        else:
            _replace_named_item(section, value)  # type: ignore[arg-type]

    base_policy_by_name = {item.name: item for item in base.policies}
    candidate_policy_by_name = {item["name"]: item for item in candidate["policies"]}
    if set(base_policy_by_name) - set(candidate_policy_by_name):
        raise CandidatePatchError("removing_mandatory_policy")
    for name, policy in base_policy_by_name.items():
        candidate_policy = candidate_policy_by_name[name]
        if policy.blocking and not candidate_policy["blocking"]:
            raise CandidatePatchError("removing_mandatory_policy")

    try:
        validated = validate_process_definition(ProcessDefinitionDocument.model_validate(candidate))
    except (ValidationError, ProcessValidationError, TypeError, ValueError) as exc:
        raise _invalid_patch() from exc
    return validated.model_dump(mode="json"), {"operations": operations}
