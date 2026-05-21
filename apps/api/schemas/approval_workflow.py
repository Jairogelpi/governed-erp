from __future__ import annotations

from pydantic import BaseModel

from erpguard.product.models import (
    ActivationGateModel,
    ApprovalDecisionModel,
    ApprovalRequestModel,
    GovernanceSummaryModel,
)


class ApprovalRequestBody(BaseModel):
    requested_by: dict
    reason: str
    context: dict = {}


class ApprovalDecisionBody(BaseModel):
    decided_by: dict
    decision: str
    reason: str


class ApprovalRequestResponse(ApprovalRequestModel):
    pass


class ApprovalDecisionResponse(ApprovalDecisionModel):
    pass


class ActivationGateResponse(ActivationGateModel):
    pass


class GovernanceSummaryResponse(GovernanceSummaryModel):
    pass
