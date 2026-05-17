from pathlib import Path

import yaml
from pydantic import ValidationError

from erpguard.core.errors import PolicyLoadError, PolicyValidationError
from erpguard.policies.schema import PolicyDefinition


def load_policy_file(path: Path | str) -> PolicyDefinition:
    policy_path = Path(path)
    try:
        raw_text = policy_path.read_text(encoding="utf-8")
    except OSError as exc:
        raise PolicyLoadError(f"Could not load policy file '{policy_path}'.") from exc

    try:
        raw_policy = yaml.safe_load(raw_text)
    except yaml.YAMLError as exc:
        raise PolicyLoadError(f"Could not parse YAML policy file '{policy_path}'.") from exc

    try:
        return PolicyDefinition.model_validate(raw_policy)
    except ValidationError as exc:
        raise PolicyValidationError(f"Policy file '{policy_path}' is invalid: {exc}") from exc


def load_formula_guard_policy() -> PolicyDefinition:
    return load_policy_file(Path("policies/odoo/formula_guard.yaml"))
