from __future__ import annotations

from erpguard.db.repositories import get_latest_write_readiness_certification_for_skill
from erpguard.product.models import WritePilotPolicyCheckModel, WritePilotPolicyViolation

_ALLOW_R1_REAL_WRITE_PILOT = False
_ALLOW_GENERIC_REAL_ODOO_WRITES = False
_ALLOW_R3_R4_REAL_WRITES = False
_PILOT_ALLOWED_MODELS = frozenset({"mail.message"})


class WritePilotPolicyService:
    def __init__(self, session) -> None:
        self.session = session

    def check(self, skill_id: str, target_model: str, request_id: str) -> WritePilotPolicyCheckModel:
        violations: list[WritePilotPolicyViolation] = []

        cert = get_latest_write_readiness_certification_for_skill(self.session, skill_id)
        if cert is None:
            violations.append(WritePilotPolicyViolation(
                code="missing_write_readiness_certification",
                message="No write readiness certification found for this skill. Complete Sprint 7 flow first.",
            ))

        if target_model not in _PILOT_ALLOWED_MODELS:
            violations.append(WritePilotPolicyViolation(
                code="model_not_whitelisted",
                message=f"Model '{target_model}' is not on the R1 pilot whitelist. Only mail.message is allowed.",
            ))

        if not _ALLOW_R1_REAL_WRITE_PILOT:
            violations.append(WritePilotPolicyViolation(
                code="feature_flag_disabled",
                message="ALLOW_R1_REAL_WRITE_PILOT=false. Enable the feature flag to allow pilot writes.",
            ))

        if _ALLOW_GENERIC_REAL_ODOO_WRITES:
            violations.append(WritePilotPolicyViolation(
                code="generic_writes_must_remain_disabled",
                message="ALLOW_GENERIC_REAL_ODOO_WRITES must remain false.",
            ))

        if _ALLOW_R3_R4_REAL_WRITES:
            violations.append(WritePilotPolicyViolation(
                code="r3_r4_writes_must_remain_disabled",
                message="ALLOW_R3_R4_REAL_WRITES must remain false.",
            ))

        return WritePilotPolicyCheckModel(
            request_id=request_id,
            skill_id=skill_id,
            passed=len(violations) == 0,
            allow_r1_real_write_pilot=_ALLOW_R1_REAL_WRITE_PILOT,
            allow_generic_real_odoo_writes=False,
            allow_r3_r4_real_writes=False,
            target_model=target_model,
            target_whitelisted=target_model in _PILOT_ALLOWED_MODELS,
            violations=violations,
        )
