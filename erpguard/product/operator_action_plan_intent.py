from __future__ import annotations

from dataclasses import dataclass

_PLAN_KEYWORDS: dict[str, list[str]] = {
    "prepare_for_run": [
        "preparar para preview", "ready to run", "preparar ejecución", "prepare run",
        "quiero hacer un preview", "listo para ejecutar", "prepare for preview",
        "ejecutar preview", "run preview", "preparar skill", "preview ready",
        "correr skill", "hacer preview", "launch preview",
    ],
    "activate_candidate": [
        "activar", "activate", "poner activo", "promotion", "promover candidato",
        "activación", "activation", "activar candidato", "promote to active",
        "quiero activar", "pasar a activo", "candidate activation",
    ],
    "fix_governance_gaps": [
        "corregir gaps", "fix gaps", "solucionar", "remediar", "arreglar governance",
        "fix governance", "fill gaps", "resolver gaps", "corregir problema",
        "completar governance", "complete governance", "fix missing",
        "falta corregir", "governance incomplete",
    ],
    "find_reusable_skill": [
        "encontrar reutilizable", "find reusable", "ya existe algo", "buscar parecida",
        "skill similar activa", "puedo reutilizar", "can i reuse", "find existing",
        "existe algo parecido", "reusar", "reuse existing", "find reuse",
    ],
    "inspect_lifecycle": [
        "inspeccionar ciclo", "estado completo", "full status", "lifecycle completo",
        "ver todo el ciclo", "full lifecycle", "ciclo de vida completo",
        "resumen completo", "complete summary", "historial completo",
        "full history", "inspect", "diagnose", "diagnóstico",
    ],
}


@dataclass(frozen=True)
class PlanIntent:
    plan_type: str
    confidence: float
    matched_keywords: list[str]


def classify_plan_intent(goal: str) -> PlanIntent:
    """Rule-based plan-type classifier — no LLM, purely deterministic."""
    lower = goal.lower()
    best_type = "unknown"
    best_score = 0.0
    best_keywords: list[str] = []

    for plan_type, keywords in _PLAN_KEYWORDS.items():
        hits = [kw for kw in keywords if kw in lower]
        if hits:
            score = len(hits) / len(keywords)
            if score > best_score:
                best_score = score
                best_type = plan_type
                best_keywords = hits

    confidence = min(best_score * 6, 1.0) if best_score > 0 else 0.15
    return PlanIntent(
        plan_type=best_type,
        confidence=round(confidence, 3),
        matched_keywords=best_keywords,
    )


def list_supported_plan_types() -> list[dict]:
    return [
        {"plan_type": "prepare_for_run", "description": "Steps to prepare a skill version for a safe preview run"},
        {"plan_type": "activate_candidate", "description": "Steps to promote a candidate version to active status"},
        {"plan_type": "fix_governance_gaps", "description": "Steps to resolve missing governance requirements"},
        {"plan_type": "find_reusable_skill", "description": "Steps to discover and evaluate reusable active skills"},
        {"plan_type": "inspect_lifecycle", "description": "Steps to perform a full lifecycle inspection of a version"},
        {"plan_type": "unknown", "description": "Fallback when goal cannot be mapped to a supported plan type"},
    ]
