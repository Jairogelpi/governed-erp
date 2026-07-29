from __future__ import annotations

import json

from erpguard.core.errors import ObjectNotFoundError
from erpguard.db.repositories import (
    create_skill_approval_request,
    get_latest_approval_request_for_skill,
    get_latest_skill_version,
    get_skill,
)
from erpguard.release_ops.models import ApprovalRequestModel


class ApprovalRequestService:
    def __init__(self, session) -> None:
        self.session = session

    def create(self, skill_id: str, requested_by: dict, reason: str, context: dict | None = None) -> ApprovalRequestModel:
        skill_row = get_skill(self.session, skill_id)
        if skill_row is None:
            raise ObjectNotFoundError(f"Skill '{skill_id}' was not found.")

        version_row = get_latest_skill_version(self.session, skill_id)
        if version_row is None:
            raise ObjectNotFoundError(f"No skill version found for skill '{skill_id}'.")

        package = json.loads(version_row.skill_package_json)
        ctx = {
            "runtime_mode": package.get("runtime_mode", "dry_run_only"),
            "write_actions": package.get("write_actions", False),
            "requires_approval_before_activation": package.get("requires_approval_before_activation", True),
            "guards": package.get("guards", []),
            **(context or {}),
        }

        row = create_skill_approval_request(
            self.session,
            skill_id=skill_id,
            skill_version_id=version_row.id,
            requested_by_json=json.dumps(requested_by, default=str),
            reason=reason,
            context_json=json.dumps(ctx, default=str),
            status="pending",
        )
        return ApprovalRequestModel.model_validate(
            {
                "request_id": row.id,
                "skill_id": row.skill_id,
                "skill_version_id": row.skill_version_id,
                "requested_by": requested_by,
                "reason": row.reason,
                "status": row.status,
                "can_execute_real_writes": False,
                "context": ctx,
                "created_at": row.created_at.isoformat(),
            }
        )

    def get_latest(self, skill_id: str) -> ApprovalRequestModel | None:
        row = get_latest_approval_request_for_skill(self.session, skill_id)
        if row is None:
            return None
        return ApprovalRequestModel.model_validate(
            {
                "request_id": row.id,
                "skill_id": row.skill_id,
                "skill_version_id": row.skill_version_id,
                "requested_by": json.loads(row.requested_by_json),
                "reason": row.reason,
                "status": row.status,
                "can_execute_real_writes": False,
                "context": json.loads(row.context_json),
                "created_at": row.created_at.isoformat(),
            }
        )
