from unittest.mock import Mock

from stery.domain import ClueVisibility, GamePhase
from stery.domain.models import (
    Character,
    Clue,
    GameRules,
    GameScript,
    InvestigationTarget,
    InvestigationTargetType,
    Truth,
)
from stery.domain.state import GameState
from stery.interfaces.cli import MysteryCliApp


def build_script() -> GameScript:
    """
    构造一个最小 CLI 调查测试剧本。
    """

    return GameScript(
        id="cli_investigate_script",
        title="CLI 调查测试剧本",
        version="v0.2.0",
        background="测试 CLI /investigate。",
        rules=GameRules(
            max_question_rounds=5,
            allow_free_question=True,
            allow_clue_search=True,
            final_vote=["suspect_character_id", "motive", "method", "key_evidence"],
        ),
        characters=[
            Character(
                id="npc_doctor",
                name="周医生",
                role="私人医生",
                is_npc=True,
                public_profile="死者的私人医生。",
            )
        ],
        npc_profiles=[],
        clues=[
            Clue(
                id="clue_body_mark",
                title="尸体颈侧针孔",
                content="死者颈侧有细小针孔。",
                visibility=ClueVisibility.LOCKED,
                unlock_phase=GamePhase.START,
            )
        ],
        investigation_targets=[
            InvestigationTarget(
                id="target_body",
                name="尸体",
                type=InvestigationTargetType.BODY,
                description="死者倒在地上。",
                search_keywords=["尸体", "死者"],
                discoverable_clue_ids=["clue_body_mark"],
            )
        ],
        truth=Truth(
            id="npc_doctor",
            murderer_id="npc_doctor",
            motive="测试动机",
            method="测试手法",
            key_clue_ids=["clue_body_mark"],
            motive_keywords=["测试"],
            method_keywords=["测试"],
            summary="测试真相。",
        ),
        timeline=[],
    )


def build_app() -> MysteryCliApp:
    """
    构造 CLI App。

    这里用 Mock 替代 NPC / RuleJudge / ClueSearchService，
    因为本测试只验证 /investigate。
    """

    script = build_script()
    state = GameState(script_id=script.id)

    runtime = Mock()
    runtime.script = script
    runtime.state = state

    return MysteryCliApp(
        runtime=runtime,
        npc_interaction_service=Mock(),
        rule_judge=Mock(),
        clue_search_service=Mock(),
        session_recorder=Mock(),
    )


def test_normalize_command_should_support_investigate_alias():
    app = build_app()

    assert _normalize_command("investigate") == "/investigate"
    assert _normalize_command("调查") == "/investigate"
    assert _normalize_command("/investigate") == "/investigate"


def test_investigate_target_by_number_should_unlock_clue_and_record_case(
    monkeypatch,
    capsys,
):
    """
    玩家输入编号 1 后，应完成调查：
    - 解锁线索
    - 写入 case_records
    - 输出新发现线索
    """

    app = build_app()

    monkeypatch.setattr("builtins.input", lambda _: "1")

    app.investigate_target()

    state = app.runtime.state

    assert "clue_body_mark" in state.unlocked_clue_ids
    assert len(state.case_records) == 1

    record = state.case_records[0]

    assert record.title == "调查：尸体"
    assert record.metadata["target_id"] == "target_body"
    assert record.metadata["newly_discovered_clue_ids"] == ["clue_body_mark"]

    output = capsys.readouterr().out

    assert "【调查结果】" in output
    assert "尸体颈侧针孔" in output


def test_resolve_investigation_target_by_name():
    app = build_app()

    targets = app.investigation_service.list_targets()

    assert app._resolve_investigation_target_id("尸体", targets) == "target_body"
    assert app._resolve_investigation_target_id("target_body", targets) == "target_body"