from __future__ import annotations

from dataclasses import dataclass

_INTENT_KEYWORDS: dict[str, list[str]] = {
    "list_active_skills": [
        "activas", "activos", "active", "lista activa", "cuáles tengo activas",
        "qué skills tengo", "show active", "list active", "todas las activas",
        "ver activas", "skills activas", "active skills",
    ],
    "find_similar": [
        "similar", "parecida", "parecido", "semejante", "alike", "resembles",
        "similar a", "find similar", "buscar similar", "similares",
    ],
    "governance_gaps": [
        "falta", "missing", "gaps", "governance", "qué falta", "what's missing",
        "qué le falta", "what is missing", "gap", "incomplete", "incompleto",
        "faltan", "necesita", "requires",
    ],
    "preview_ready": [
        "preview", "lista para preview", "ready for preview", "preview ready",
        "puede hacer preview", "preparada para preview", "listo para preview",
    ],
    "next_step": [
        "siguiente paso", "next step", "qué hago", "what should", "recomienda",
        "recommend", "qué debo", "acción siguiente", "siguiente acción",
        "próximo paso", "siguiente", "qué hacer", "advise", "guide",
    ],
    "lifecycle_status": [
        "estado", "status", "lifecycle", "historial", "history", "ciclo de vida",
        "cuál es el estado", "what is the status", "resumen", "summary",
        "lifecycle summary", "resume",
    ],
    "reuse_suggestions": [
        "reutilizar", "reuse", "reusar", "puedo reutilizar", "can I reuse",
        "already exists", "ya existe", "sugerencia de reutilización", "reuso",
    ],
    "search_skills": [
        "buscar", "search", "find", "encontrar", "busca", "encuentra",
        "qué skills", "what skills", "skills disponibles", "available skills",
        "mostrar", "show skills",
    ],
}


@dataclass(frozen=True)
class IntentClassification:
    intent: str
    confidence: float
    matched_keywords: list[str]


def classify_intent(query: str) -> IntentClassification:
    """Rule-based intent classifier — no LLM, purely deterministic."""
    lower = query.lower()
    best_intent = "search_skills"
    best_score = 0.0
    best_keywords: list[str] = []

    for intent, keywords in _INTENT_KEYWORDS.items():
        hits: list[str] = []
        for kw in keywords:
            if kw in lower:
                hits.append(kw)
        if hits:
            score = len(hits) / len(keywords)
            if score > best_score:
                best_score = score
                best_intent = intent
                best_keywords = hits

    confidence = min(best_score * 5, 1.0) if best_score > 0 else 0.2
    return IntentClassification(
        intent=best_intent,
        confidence=round(confidence, 3),
        matched_keywords=best_keywords,
    )


def list_supported_intents() -> list[dict]:
    return [
        {"intent": "list_active_skills", "description": "List all currently active governed skill versions"},
        {"intent": "find_similar", "description": "Find skill versions similar to a given version"},
        {"intent": "governance_gaps", "description": "Explain what governance steps are missing for a version"},
        {"intent": "preview_ready", "description": "List active versions that are ready for or have completed preview"},
        {"intent": "next_step", "description": "Recommend the next safe governance action for a version"},
        {"intent": "lifecycle_status", "description": "Summarise the full lifecycle state of a version"},
        {"intent": "reuse_suggestions", "description": "Suggest existing active skills that could be reused"},
        {"intent": "search_skills", "description": "Search the skill registry by keyword"},
    ]
