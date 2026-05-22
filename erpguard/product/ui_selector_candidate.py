from __future__ import annotations

from dataclasses import dataclass

_PRIORITY: list[str] = ["data-testid", "aria-label", "name", "placeholder"]


@dataclass(frozen=True)
class SelectorCandidate:
    selector: str
    attr_used: str
    confidence: str


def best_selector(attrs: dict[str, str | None], tag: str = "", text: str = "") -> SelectorCandidate | None:
    for attr in _PRIORITY:
        value = attrs.get(attr)
        if value:
            return SelectorCandidate(
                selector=f"[{attr}='{value}']",
                attr_used=attr,
                confidence="high" if attr == "data-testid" else "medium",
            )
    if text:
        clean = text.strip()[:40]
        tag_part = tag.lower() if tag else "element"
        return SelectorCandidate(
            selector=f"{tag_part}:text('{clean}')",
            attr_used="text",
            confidence="low",
        )
    return None


def redact_secret_value(field_name: str, field_type: str, value: str) -> str:
    if field_type.lower() == "password":
        return "[REDACTED]"
    keywords = ["password", "token", "secret", "key", "api_key", "apikey", "auth", "credential"]
    name_lower = field_name.lower()
    if any(k in name_lower for k in keywords):
        return "[REDACTED]"
    return value


def normalize_selector(raw: str | None) -> str | None:
    if not raw:
        return None
    return raw.strip()
