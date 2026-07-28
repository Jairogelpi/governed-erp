from __future__ import annotations

from erpguard.product.models import (
    AutomationDraftModel,
    BusinessAnalysisRequest,
    BusinessAnalysisResult,
    BusinessOpportunityModel,
    BusinessSignalModel,
    BusinessSnapshotModel,
    OpportunityROIModel,
    OpportunityScanModel,
)


class ProductAnalysisRequest(BusinessAnalysisRequest):
    pass


class ProductAnalysisSnapshotResponse(BusinessSnapshotModel):
    pass


class ProductAnalysisSignalResponse(BusinessSignalModel):
    pass


class ProductOpportunityROIResponse(OpportunityROIModel):
    pass


class ProductAnalysisOpportunityResponse(BusinessOpportunityModel):
    pass


class ProductOpportunityScanResponse(OpportunityScanModel):
    pass


class ProductAnalysisResponse(BusinessAnalysisResult):
    pass


class ProductAutomationDraftResponse(AutomationDraftModel):
    pass
