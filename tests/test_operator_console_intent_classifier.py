"""Sprint 41 — Operator Console Intent Classifier unit tests."""
from __future__ import annotations


from erpguard.product.operator_console_intent_classifier import classify_intent, list_supported_intents


def test_list_active_skills_intent_spanish():
    r = classify_intent("¿Qué skills tengo activas?")
    assert r.intent == "list_active_skills"
    assert r.confidence > 0


def test_list_active_skills_intent_english():
    r = classify_intent("show active skills")
    assert r.intent == "list_active_skills"


def test_governance_gaps_intent():
    r = classify_intent("qué falta para activar esta automatización")
    assert r.intent == "governance_gaps"


def test_next_step_intent():
    r = classify_intent("recomiéndame el siguiente paso seguro")
    assert r.intent == "next_step"


def test_preview_ready_intent():
    r = classify_intent("¿Qué skill está lista para preview?")
    assert r.intent == "preview_ready"


def test_reuse_suggestions_intent():
    r = classify_intent("¿Puedo reutilizar alguna skill existente?")
    assert r.intent == "reuse_suggestions"


def test_lifecycle_status_intent():
    r = classify_intent("muéstrame el estado y el lifecycle de esta versión")
    assert r.intent == "lifecycle_status"


def test_find_similar_intent():
    r = classify_intent("buscar skills similares")
    assert r.intent == "find_similar"


def test_unknown_query_defaults_to_search():
    r = classify_intent("formula review")
    assert r.intent in ("search_skills", "find_similar", "list_active_skills")


def test_classification_has_confidence():
    r = classify_intent("¿Qué skills tengo activas?")
    assert 0 <= r.confidence <= 1.0


def test_matched_keywords_present():
    r = classify_intent("siguiente paso seguro para activar")
    assert len(r.matched_keywords) >= 1


def test_list_supported_intents_complete():
    intents = list_supported_intents()
    intent_names = {i["intent"] for i in intents}
    expected = {
        "list_active_skills", "find_similar", "governance_gaps", "preview_ready",
        "next_step", "lifecycle_status", "reuse_suggestions", "search_skills",
    }
    assert expected == intent_names
