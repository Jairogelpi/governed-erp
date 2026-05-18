import json

from erpguard.db.repositories import (
    create_skill,
    create_skill_run,
    create_skill_run_step,
    create_skill_version,
    finish_skill_run,
    get_latest_skill_version,
    get_skill,
    list_skills,
)
from erpguard.db.session import SessionLocal, init_db


def test_skill_registry_repository_roundtrip():
    init_db()
    session = SessionLocal()
    try:
        skill = create_skill(session, "Repo Skill", "Repository level skill test")
        version = create_skill_version(
            session=session,
            skill_id=skill.id,
            version="1.0.0",
            skill_package_json=json.dumps({"skill_id": "repo_skill"}),
            runtime_type="deterministic_browser",
            llm_required_for_repeated_runs=False,
        )

        assert get_skill(session, skill.id).name == "Repo Skill"
        assert get_latest_skill_version(session, skill.id).id == version.id
        assert json.loads(version.skill_package_json)["skill_id"] == "repo_skill"
        assert version.llm_required_for_repeated_runs is False
        assert any(row.id == skill.id for row in list_skills(session))

        skill_run = create_skill_run(
            session=session,
            skill_id=skill.id,
            skill_version_id=version.id,
            status="running",
            input_json=json.dumps({"order_reference": "SO-VALID"}),
        )
        step = create_skill_run_step(
            session=session,
            skill_run_id=skill_run.id,
            step_id="open_orders",
            step_type="navigate",
            status="passed",
            input_json=json.dumps({"target": "/fake-erp/sales/orders"}),
            output_json=json.dumps({"ok": True}),
        )
        finished = finish_skill_run(
            session=session,
            skill_run_id=skill_run.id,
            status="passed",
            output_json=json.dumps({"decision": "allow"}),
            decision="allow",
            estimated_tokens_saved=120,
        )

        assert step.step_id == "open_orders"
        assert finished.status == "passed"
        assert finished.estimated_tokens_saved == 120
        assert finished.finished_at is not None
    finally:
        session.close()