from __future__ import annotations

from erpguard.product.models import (
    CompiledSkillModel,
    DraftReviewModel,
    DraftValidationResultModel,
    DryRunProofModel,
)


class DraftReviewResponse(DraftReviewModel):
    pass


class DraftValidationResultResponse(DraftValidationResultModel):
    pass


class CompiledSkillResponse(CompiledSkillModel):
    pass


class DryRunProofResponse(DryRunProofModel):
    pass
