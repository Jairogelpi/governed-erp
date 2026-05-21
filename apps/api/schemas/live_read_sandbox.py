from __future__ import annotations

from pydantic import BaseModel

from erpguard.product.models import (
    ConnectionContextModel,
    LiveReadEvidenceModel,
    LiveReadExecutionRequestModel,
    LiveReadPolicyResult,
    LiveReadRunModel,
)


class LiveReadExecutionRequestBody(BaseModel):
    requested_by: dict
    inputs: dict = {}


class LiveReadExecutionRequestResponse(LiveReadExecutionRequestModel):
    pass


class LiveReadRunResponse(LiveReadRunModel):
    pass


class LiveReadEvidenceResponse(LiveReadEvidenceModel):
    pass


class ConnectionContextResponse(ConnectionContextModel):
    pass


class LiveReadPolicyResponse(LiveReadPolicyResult):
    pass
