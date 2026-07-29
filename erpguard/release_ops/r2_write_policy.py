from __future__ import annotations

from erpguard.adapters.odoo.r2_write_client import R2_ALLOWED_WRITE_FIELDS, R2_ALLOWED_WRITE_MODELS
from erpguard.db.repositories import get_latest_write_readiness_certification_for_skill
from erpguard.product.models import R2WritePilotPolicyCheckModel, R2WritePilotPolicyViolation

_ALLOW_R2_REAL_WRITE_PILOT = False
_ALLOW_GENERIC_REAL_ODOO_WRITES = False
_ALLOW_R3_R4_REAL_WRITES = False
_ALLOWED_ENVIRONMENTS = frozenset({"staging", "demo"})


class R2WritePilotPolicyService:
    def __init__(self, session) -> None:
        self.session = session

    def check(
        self,
        skill_id: str,
        request_id: str,
        target_model: str,
        target_fields: list[str],
        environment: str,
        approver_1_id: str,
        approver_2_id: str,
    ) -> R2WritePilotPolicyCheckModel:
        violations: list[R2WritePilotPolicyViolation] = []

        cert = get_latest_write_readiness_certification_for_skill(self.session, skill_id)
        if cert is None:
            violations.append(R2WritePilotPolicyViolation(
                code="missing_write_readiness_certification",
                message="No write readiness certification found for this skill. Complete Sprint 7 first.",
            ))

        if target_model not in R2_ALLOWED_WRITE_MODELS:
            violations.append(R2WritePilotPolicyViolation(
                code="model_not_whitelisted",
                message=f"Model '{target_model}' is not on the R2 whitelist. Only {sorted(R2_ALLOWED_WRITE_MODELS)} allowed.",
            ))

        disallowed_fields = set(target_fields) - R2_ALLOWED_WRITE_FIELDS
        if disallowed_fields:
            violations.append(R2WritePilotPolicyViolation(
                code="fields_not_whitelisted",
                message=f"Fields {sorted(disallowed_fields)} not allowed. Only {sorted(R2_ALLOWED_WRITE_FIELDS)} allowed.",
            ))

        if environment not in _ALLOWED_ENVIRONMENTS:
            violations.append(R2WritePilotPolicyViolation(
                code="environment_not_allowed",
                message=f"Environment '{environment}' not allowed for R2 writes. Must be staging or demo.",
            ))

        if not approver_1_id or not approver_2_id:
            violations.append(R2WritePilotPolicyViolation(
                code="missing_approvers",
                message="Both approver_1 and approver_2 must be provided.",
            ))
        elif approver_1_id == approver_2_id:
            violations.append(R2WritePilotPolicyViolation(
                code="duplicate_approvers",
                message="approver_1 and approver_2 must be distinct people.",
            ))

        if not _ALLOW_R2_REAL_WRITE_PILOT:
            violations.append(R2WritePilotPolicyViolation(
                code="feature_flag_disabled",
                message="ALLOW_R2_REAL_WRITE_PILOT=false. Enable the feature flag to allow R2 pilot writes.",
            ))

        if _ALLOW_GENERIC_REAL_ODOO_WRITES:
            violations.append(R2WritePilotPolicyViolation(
                code="generic_writes_must_remain_disabled",
                message="ALLOW_GENERIC_REAL_ODOO_WRITES must remain false.",
            ))

        if _ALLOW_R3_R4_REAL_WRITES:
            violations.append(R2WritePilotPolicyViolation(
                code="r3_r4_writes_must_remain_disabled",
                message="ALLOW_R3_R4_REAL_WRITES must remain false.",
            ))

        return R2WritePilotPolicyCheckModel(
            request_id=request_id,
            skill_id=skill_id,
            passed=len(violations) == 0,
            allow_r2_real_write_pilot=_ALLOW_R2_REAL_WRITE_PILOT,
            allow_generic_real_odoo_writes=False,
            allow_r3_r4_real_writes=False,
            target_model=target_model,
            target_model_whitelisted=target_model in R2_ALLOWED_WRITE_MODELS,
            target_fields=target_fields,
            target_fields_whitelisted=not disallowed_fields if target_fields else False,
            violations=violations,
        )
