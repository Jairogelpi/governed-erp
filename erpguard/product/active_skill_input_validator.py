from __future__ import annotations

from dataclasses import dataclass, field

_FAKE_ERP_MARKER = "/fake-erp"


@dataclass(frozen=True)
class InputValidationResult:
    ok: bool
    checks: list[dict] = field(default_factory=list)
    sanitized_inputs: dict = field(default_factory=dict)
    rejection_reasons: list[str] = field(default_factory=list)


class ActiveSkillInputValidatorService:
    _MAX_KEY_LENGTH = 64
    _MAX_VALUE_LENGTH = 512

    def validate(self, target_base_url: str, inputs: dict | None = None) -> InputValidationResult:
        checks: list[dict] = []
        rejections: list[str] = []
        sanitized: dict = {}

        target_ok = isinstance(target_base_url, str) and _FAKE_ERP_MARKER in target_base_url
        if not target_ok:
            rejections.append("target_base_url must be a string containing /fake-erp.")
        checks.append({"check": "target_base_url_is_fake_erp", "ok": target_ok})

        inputs = inputs or {}
        if not isinstance(inputs, dict):
            rejections.append("inputs must be a dict.")
            checks.append({"check": "inputs_is_dict", "ok": False})
        else:
            checks.append({"check": "inputs_is_dict", "ok": True})
            for key, value in inputs.items():
                if not isinstance(key, str):
                    rejections.append(f"Input key {key!r} is not a string.")
                    continue
                if len(key) > self._MAX_KEY_LENGTH:
                    rejections.append(f"Input key {key!r} exceeds max length {self._MAX_KEY_LENGTH}.")
                    continue
                if isinstance(value, (dict, list)):
                    rejections.append(f"Input value for {key!r} must be scalar (str/int/float/bool), not {type(value).__name__}.")
                    continue
                if isinstance(value, str) and len(value) > self._MAX_VALUE_LENGTH:
                    rejections.append(f"Input value for {key!r} exceeds max length {self._MAX_VALUE_LENGTH}.")
                    continue
                sanitized[key] = value

            checks.append({"check": "inputs_sanitized", "ok": True, "input_count": len(sanitized)})

        ok = len(rejections) == 0
        return InputValidationResult(
            ok=ok, checks=checks,
            sanitized_inputs=sanitized,
            rejection_reasons=rejections,
        )
