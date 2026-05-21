from __future__ import annotations

from pydantic import BaseModel

from erpguard.product.models import (
    BlockedWriteEvidenceModel,
    ExecutionRequestModel,
    ExecutionRunModel,
    ExecutionTimelineModel,
)


class ExecutionRequestBody(BaseModel):
    requested_by: dict
    inputs: dict = {}


class ExecutionRequestResponse(ExecutionRequestModel):
    pass


class ExecutionRunResponse(ExecutionRunModel):
    pass


class ExecutionTimelineResponse(ExecutionTimelineModel):
    pass


class BlockedWriteEvidenceResponse(BlockedWriteEvidenceModel):
    pass


class PolicyCheckResponse(BaseModel):
    passed: bool
    can_execute_real_writes: bool = False
    real_erp_writes_enabled: bool = False
    violations: list[dict] = []
