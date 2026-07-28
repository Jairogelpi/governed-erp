from __future__ import annotations

import yaml

from erpguard.domain.processes.models import ProcessDefinitionDocument


class ProcessValidationError(ValueError):
    pass


def validate_process_definition(definition: ProcessDefinitionDocument) -> ProcessDefinitionDocument:
    object_names = {item.name for item in definition.objects}
    event_names = {item.name for item in definition.events}
    decision_names = {item.name for item in definition.decisions}
    if len(object_names) != len(definition.objects):
        raise ProcessValidationError("duplicate_process_object")
    if len(event_names) != len(definition.events):
        raise ProcessValidationError("duplicate_process_event")
    if any(item.object not in object_names for item in definition.events):
        raise ProcessValidationError("event_object_reference_missing")
    if any(item.applies_to not in event_names for item in definition.decisions):
        raise ProcessValidationError("decision_event_reference_missing")
    if any(item.decision not in decision_names for item in definition.policies):
        raise ProcessValidationError("policy_decision_reference_missing")
    for metric in definition.metrics:
        if metric.start_event and metric.start_event not in event_names:
            raise ProcessValidationError("metric_start_event_reference_missing")
        if metric.end_event and metric.end_event not in event_names:
            raise ProcessValidationError("metric_end_event_reference_missing")
    for fixture in definition.fixtures:
        if any(event not in event_names for event in fixture.events):
            raise ProcessValidationError("fixture_event_reference_missing")
    return definition


def load_process_yaml(text: str) -> ProcessDefinitionDocument:
    try:
        raw = yaml.safe_load(text)
        if not isinstance(raw, dict):
            raise ProcessValidationError("process_yaml_root_must_be_mapping")
        return validate_process_definition(ProcessDefinitionDocument.model_validate(raw))
    except ProcessValidationError:
        raise
    except (yaml.YAMLError, ValueError) as exc:
        raise ProcessValidationError("invalid_process_definition") from exc
