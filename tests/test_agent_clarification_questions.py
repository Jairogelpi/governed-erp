from __future__ import annotations

from erpguard.product.agent_clarification_questions import generate_questions


def test_low_confidence_adds_describe_question():
    questions = generate_questions("unknown", "unknown", "manual", "low")
    question_texts = [q.question for q in questions]
    assert any("describe" in q.lower() or "specifically" in q.lower() for q in question_texts)


def test_unknown_entity_adds_entity_question():
    questions = generate_questions("read", "unknown", "manual", "medium")
    question_texts = [q.question for q in questions]
    assert any("object" in q.lower() or "target" in q.lower() for q in question_texts)


def test_unknown_action_adds_action_question():
    questions = generate_questions("unknown", "sales_order", "manual", "medium")
    option_sets = [q.options for q in questions]
    assert any("read" in opts for opts in option_sets)


def test_write_action_adds_approver_question():
    questions = generate_questions("confirm", "sales_order", "manual", "high")
    question_texts = [q.question for q in questions]
    assert any("approv" in q.lower() for q in question_texts)


def test_financial_entity_adds_journal_question():
    questions = generate_questions("validate", "payment", "manual", "high")
    question_texts = [q.question for q in questions]
    assert any("journal" in q.lower() for q in question_texts)


def test_high_confidence_known_all_fewer_questions():
    questions = generate_questions("read", "sales_order", "scheduled", "high")
    assert len(questions) <= 2


def test_question_ids_are_unique():
    questions = generate_questions("unknown", "unknown", "manual", "low")
    ids = [q.question_id for q in questions]
    assert len(ids) == len(set(ids))
