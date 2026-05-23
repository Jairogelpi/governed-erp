from __future__ import annotations

from pydantic import BaseModel, Field


class ClarificationQuestion(BaseModel):
    question_id: str
    question: str
    reason: str
    answer_type: str = "text"
    options: list[str] = Field(default_factory=list)


def generate_questions(
    action_type: str,
    target_entity: str,
    trigger_type: str,
    confidence: str,
) -> list[ClarificationQuestion]:
    questions: list[ClarificationQuestion] = []
    qid = 1

    if confidence == "low":
        questions.append(ClarificationQuestion(
            question_id=f"q{qid}",
            question="Could you describe more specifically what ERP operation you want to automate?",
            reason="Intent confidence is low — a more detailed description will produce a better proposal.",
            answer_type="text",
        ))
        qid += 1

    if target_entity == "unknown":
        questions.append(ClarificationQuestion(
            question_id=f"q{qid}",
            question=(
                "Which ERP object should this automation target? "
                "(sales orders, invoices, partners, products, inventory, payments…)"
            ),
            reason="Target entity could not be determined from the request.",
            answer_type="choice",
            options=["sales_order", "invoice", "partner", "product", "purchase_order", "inventory", "payment", "other"],
        ))
        qid += 1

    if action_type == "unknown":
        questions.append(ClarificationQuestion(
            question_id=f"q{qid}",
            question=(
                "What should the automation do with those records? "
                "(read, validate, confirm, update, send, report, create, delete)"
            ),
            reason="Action type could not be determined from the request.",
            answer_type="choice",
            options=["read", "validate", "confirm", "update", "send", "report", "create", "delete"],
        ))
        qid += 1

    if trigger_type == "manual":
        questions.append(ClarificationQuestion(
            question_id=f"q{qid}",
            question="Should this run on a schedule, be triggered by an ERP event, or run on demand?",
            reason="Trigger type determines the automation architecture.",
            answer_type="choice",
            options=["manual (on demand)", "scheduled (specify interval)", "event-driven (on ERP event)"],
        ))
        qid += 1

    if action_type in ("confirm", "update", "delete", "create"):
        questions.append(ClarificationQuestion(
            question_id=f"q{qid}",
            question="Who should approve this operation before it executes — a specific role or any authorised user?",
            reason="Write operations require a defined approver in the automation design.",
            answer_type="text",
        ))
        qid += 1

    if target_entity in ("invoice", "payment"):
        questions.append(ClarificationQuestion(
            question_id=f"q{qid}",
            question="Should this automation be restricted to specific accounting journals or companies?",
            reason="Financial operations should be scoped to avoid cross-company or journal errors.",
            answer_type="text",
        ))
        qid += 1

    return questions
