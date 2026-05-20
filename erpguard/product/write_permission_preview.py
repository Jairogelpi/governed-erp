from __future__ import annotations

from erpguard.product.models import WriteDetectedCandidateModel, WritePermissionPreviewModel

_PERMISSIONS_BY_METHOD: dict[str, list[str]] = {
    "create": ["create"],
    "write": ["write"],
    "unlink": ["unlink"],
    "copy": ["read", "create"],
    "action_confirm": ["write", "execute"],
    "action_done": ["write", "execute"],
    "action_cancel": ["write", "execute"],
    "button_confirm": ["write", "execute"],
    "button_validate": ["write", "execute"],
    "button_approve": ["write", "execute"],
}


class WritePermissionPreviewService:
    def compute(self, skill_id: str, candidates: list[WriteDetectedCandidateModel]) -> WritePermissionPreviewModel:
        required: set[str] = set()
        for c in candidates:
            perms = _PERMISSIONS_BY_METHOD.get(c.write_method, ["write"])
            for p in perms:
                required.add(f"{c.odoo_model}:{p}")

        required_list = sorted(required)
        # All permissions are "missing" because writes are not enabled — this is a preview only
        return WritePermissionPreviewModel(
            skill_id=skill_id,
            required_odoo_permissions=required_list,
            missing_permissions=required_list,
            permission_gaps=[f"ALLOW_REAL_ODOO_WRITES=false blocks all {len(required_list)} required permissions"],
            can_execute_real_writes=False,
            real_erp_writes_enabled=False,
        )
