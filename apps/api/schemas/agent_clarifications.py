from __future__ import annotations

from pydantic import BaseModel, Field


class QuestionAnswerSchema(BaseModel):
    question_id: str
    answer_text: str


class SubmitAnswersRequest(BaseModel):
    answers: list[QuestionAnswerSchema] = Field(default_factory=list)


class ClarificationQuestionSummarySchema(BaseModel):
    question_id: str
    question: str
    answer_type: str
    answered: bool
    answer_text: str | None = None


class ClarificationStateResponse(BaseModel):
    proposal_id: str
    total_questions: int
    answered_count: int
    pending_count: int
    all_answered: bool
    questions: list[ClarificationQuestionSummarySchema] = Field(default_factory=list)
    is_advisory_only: bool = True
    can_execute: bool = False


class SubmitAnswersResponse(BaseModel):
    proposal_id: str
    submitted: list[str] = Field(default_factory=list)
    skipped_unknown: list[str] = Field(default_factory=list)
    total_submitted: int = 0
    is_advisory_only: bool = True
    can_execute: bool = False


class MappingActionRequest(BaseModel):
    reason: str | None = None


class MappingActionResponse(BaseModel):
    proposal_id: str
    mapping_key: str
    action: str
    reason: str | None = None
    previous_action: str | None = None
    is_advisory_only: bool = True
    can_execute: bool = False


class ClarificationCompletenessResponse(BaseModel):
    proposal_id: str
    questions_total: int
    questions_answered: int
    questions_pct: int
    mappings_total: int
    mappings_confirmed: int
    mappings_rejected: int
    mappings_pct: int
    mapping_issues: list[str] = Field(default_factory=list)
    overall_complete: bool
    is_advisory_only: bool = True
    can_execute: bool = False
    next_steps: list[str] = Field(default_factory=list)


class DraftMetadataRefreshResponse(BaseModel):
    draft_id: str
    proposal_id: str
    refreshed: bool
    answers_applied: int
    confirmations_applied: int
    runtime_mode: str = "dry_run_only"
    write_actions: bool = False
    can_execute: bool = False
    is_advisory_only: bool = True
    blocking_reason: str | None = None


class AuditEntrySchema(BaseModel):
    event_id: str
    event_type: str
    detail: dict = Field(default_factory=dict)
    created_at: str


class ClarificationAuditResponse(BaseModel):
    proposal_id: str
    event_count: int
    events: list[AuditEntrySchema] = Field(default_factory=list)
    is_advisory_only: bool = True
    can_execute: bool = False
