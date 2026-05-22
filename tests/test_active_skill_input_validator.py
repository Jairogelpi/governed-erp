from __future__ import annotations

from erpguard.product.active_skill_input_validator import ActiveSkillInputValidatorService


_FAKE_ERP_URL = "http://localhost:8000/fake-erp"


def test_valid_inputs():
    svc = ActiveSkillInputValidatorService()
    result = svc.validate(_FAKE_ERP_URL, {"order_reference": "SO-VALID"})
    assert result.ok is True
    assert result.sanitized_inputs == {"order_reference": "SO-VALID"}


def test_empty_inputs_allowed():
    svc = ActiveSkillInputValidatorService()
    result = svc.validate(_FAKE_ERP_URL, {})
    assert result.ok is True


def test_none_inputs_allowed():
    svc = ActiveSkillInputValidatorService()
    result = svc.validate(_FAKE_ERP_URL, None)
    assert result.ok is True


def test_non_fake_erp_url_rejected():
    svc = ActiveSkillInputValidatorService()
    result = svc.validate("http://production-erp.example.com", {})
    assert result.ok is False
    assert any("fake-erp" in r for r in result.rejection_reasons)


def test_nested_dict_input_rejected():
    svc = ActiveSkillInputValidatorService()
    result = svc.validate(_FAKE_ERP_URL, {"meta": {"key": "value"}})
    assert result.ok is False
    assert "meta" not in result.sanitized_inputs


def test_list_input_rejected():
    svc = ActiveSkillInputValidatorService()
    result = svc.validate(_FAKE_ERP_URL, {"items": [1, 2, 3]})
    assert result.ok is False


def test_oversized_value_rejected():
    svc = ActiveSkillInputValidatorService()
    long_value = "x" * 1000
    result = svc.validate(_FAKE_ERP_URL, {"big": long_value})
    assert result.ok is False


def test_oversized_key_rejected():
    svc = ActiveSkillInputValidatorService()
    long_key = "k" * 100
    result = svc.validate(_FAKE_ERP_URL, {long_key: "value"})
    assert result.ok is False


def test_inputs_not_dict_rejected():
    svc = ActiveSkillInputValidatorService()
    result = svc.validate(_FAKE_ERP_URL, "not_a_dict")
    assert result.ok is False


def test_scalar_input_types_accepted():
    svc = ActiveSkillInputValidatorService()
    result = svc.validate(_FAKE_ERP_URL, {"s": "x", "i": 1, "f": 1.5, "b": True})
    assert result.ok is True
    assert len(result.sanitized_inputs) == 4
