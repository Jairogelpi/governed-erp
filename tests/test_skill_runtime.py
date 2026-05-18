import builtins

from fastapi.testclient import TestClient

from apps.api.main import app


client = TestClient(app)


def create_skill() -> str:
    response = client.post(
        "/v1/skills",
        json={
            "name": "Runtime No LLM Skill",
            "description": "Deterministic run path smoke test.",
            "runtime_type": "deterministic_browser",
            "llm_required_for_repeated_runs": False,
            "skill_package": {
                "skill_id": "runtime_no_llm_skill",
                "inputs": {"order_reference": "string"},
                "guards": ["formula_guard"],
                "workflow": [],
            },
        },
    )
    assert response.status_code == 200
    return response.json()["skill_id"]


def test_deterministic_runtime_path_uses_no_llm_and_returns_allow_for_valid_order(monkeypatch):
    original_import = builtins.__import__

    def guarded_import(name, globals=None, locals=None, fromlist=(), level=0):
        blocked_prefixes = ("openai", "anthropic", "langchain", "llm")
        if name.startswith(blocked_prefixes):
            raise AssertionError(f"Unexpected LLM import: {name}")
        return original_import(name, globals, locals, fromlist, level)

    monkeypatch.setattr(builtins, "__import__", guarded_import)

    skill_id = create_skill()
    response = client.post(f"/v1/skills/{skill_id}/run", json={"inputs": {"order_reference": "SO-VALID"}})

    assert response.status_code == 200
    body = response.json()
    assert body["decision"] == "allow"
    assert body["token_economics"]["estimated_tokens_saved"] == 2000