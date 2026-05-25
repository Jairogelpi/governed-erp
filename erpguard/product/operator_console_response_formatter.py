from __future__ import annotations

from erpguard.product.operator_console_query_router import RoutedResult


def _follow_ups(intent: str, version_id: str | None) -> list[str]:
    base = []
    if version_id:
        base += [
            f"What governance gaps does version {version_id} have?",
            f"What is the next step for version {version_id}?",
            f"Show the lifecycle summary for version {version_id}.",
        ]
    else:
        base += [
            "List all active skills.",
            "Search for skills with formula guard.",
            "Show reuse suggestions for formula review.",
        ]
    return base[:3]


def format_response(intent: str, routed: RoutedResult) -> str:
    """Produce a human-readable advisory summary — no mutation, no execution."""
    data = routed.data
    result_type = routed.result_type

    if result_type == "skill_list":
        results = getattr(data, "results", [])
        if not results:
            return "No skill versions found matching your query."
        names = ", ".join(f"'{h.name}' ({h.status})" for h in results[:5])
        count = data.total_found
        return (
            f"Found {count} skill version(s). Top results: {names}. "
            f"Advisory only — no versions were executed or modified."
        )

    if result_type == "similar_list":
        similar = getattr(data, "similar", [])
        if not similar:
            return f"No similar skills found for version '{data.reference_name}'."
        names = ", ".join(f"'{h.name}' (score={h.similarity_score})" for h in similar[:3])
        return (
            f"Skills similar to '{data.reference_name}': {names}. "
            f"Similarity is based on shared guard names and step types. Advisory only."
        )

    if result_type == "gap_list":
        gaps = getattr(data, "gaps", [])
        if not gaps:
            return "No governance gaps found. This version appears fully governed."
        blocking = [g for g in gaps if g.severity == "blocking"]
        warnings = [g for g in gaps if g.severity == "warning"]
        msg = f"Found {len(gaps)} governance gap(s)."
        if blocking:
            types = ", ".join(g.gap_type for g in blocking[:3])
            msg += f" Blocking: {types}."
        if warnings:
            types = ", ".join(g.gap_type for g in warnings[:2])
            msg += f" Warnings: {types}."
        msg += " Advisory only — no changes were made."
        return msg

    if result_type == "next_steps":
        steps = getattr(data, "next_steps", [])
        if not steps:
            return "No next steps found."
        if getattr(data, "all_steps_complete", False):
            return "All governance steps are complete. This version is fully governed."
        step_descs = "; ".join(
            f"({s.severity}) {s.action}" for s in steps[:3]
        )
        return (
            f"Recommended next steps ({len(steps)} total): {step_descs}. "
            f"Advisory only — no actions were executed."
        )

    if result_type == "lifecycle_summary":
        governance_status = getattr(data, "governance_status", "unknown")
        name = getattr(data, "name", "unknown")
        events = getattr(data, "lifecycle_events", [])
        has_preview = getattr(data, "has_run_preview", False)
        return (
            f"Skill '{name}' is in governance status '{governance_status}'. "
            f"Lifecycle events: {len(events)}. "
            f"Run preview completed: {has_preview}. Advisory only."
        )

    if result_type == "reuse_list":
        suggestions = getattr(data, "suggestions", [])
        if not suggestions:
            return "No reuse suggestions found. No active governed skill matches your query."
        names = ", ".join(f"'{s.name}' (score={s.similarity_score})" for s in suggestions[:3])
        return (
            f"Reuse suggestions: {names}. "
            f"These are existing active skills. Advisory only — no versions were forked or modified."
        )

    return "Query processed. Advisory only — no actions were executed."
