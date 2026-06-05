# tests/unit/test_investigation_service.py

import pytest

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
from stery.investigation.investigation_service import (
    InvestigationService,
    InvestigationTargetNotFoundError,
)


def build_script() -> GameScript:
    """
    构造一个最小调查服务测试剧本。

    这个剧本只服务 InvestigationService 单元测试：
    - 不测试 RuleJudge
    - 不测试 NPC
    - 不测试 CLI
    """

    return GameScript(
        id="test_investigation_script",
        title="调查服务测试剧本",
        version="v0.2.0",
        background="用于测试调查对象发现线索。",
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
                id="clue_public_scene",
                title="公开现场状态",
                content="书房内有明显调查痕迹。",
                visibility=ClueVisibility.PUBLIC,
                unlock_phase=GamePhase.START,
            ),
            Clue(
                id="clue_body_mark",
                title="尸体颈侧针孔",
                content="死者颈侧有细小针孔。",
                visibility=ClueVisibility.LOCKED,
                unlock_phase=GamePhase.START,
            ),
            Clue(
                id="clue_injector",
                title="异常注入器",
                content="注入器批号与登记记录不一致。",
                visibility=ClueVisibility.LOCKED,
                unlock_phase=GamePhase.START,
            ),
            Clue(
                id="clue_hidden_truth",
                title="隐藏真相线索",
                content="这条线索不应该通过普通调查暴露。",
                visibility=ClueVisibility.HIDDEN,
                unlock_phase=GamePhase.START,
            ),
        ],
        investigation_targets=[
            InvestigationTarget(
                id="target_body",
                name="尸体",
                type=InvestigationTargetType.BODY,
                description="死者倒在书房地毯上。",
                search_keywords=["尸体", "死者"],
                discoverable_clue_ids=["clue_body_mark"],
            ),
            InvestigationTarget(
                id="target_injector",
                name="注入器",
                type=InvestigationTargetType.ITEM,
                description="死者手边有一支空注入器。",
                search_keywords=["注入器"],
                discoverable_clue_ids=["clue_injector"],
            ),
            InvestigationTarget(
                id="target_room",
                name="书房",
                type=InvestigationTargetType.ROOM,
                description="案发现场。",
                search_keywords=["书房", "现场"],
                discoverable_clue_ids=["clue_public_scene"],
            ),
            InvestigationTarget(
                id="target_hidden",
                name="隐藏目标",
                type=InvestigationTargetType.ITEM,
                description="用于测试 HIDDEN 不可普通解锁。",
                search_keywords=["隐藏"],
                discoverable_clue_ids=["clue_hidden_truth"],
            ),
            InvestigationTarget(
                id="target_empty",
                name="空目标",
                type=InvestigationTargetType.ITEM,
                description="这个目标没有绑定任何线索。",
                search_keywords=["空"],
                discoverable_clue_ids=[],
            ),
        ],
        truth=Truth(
            id="npc_doctor",
            murderer_id="npc_doctor",
            motive="测试动机",
            method="测试手法",
            key_clue_ids=["clue_body_mark", "clue_injector"],
            motive_keywords=["测试"],
            method_keywords=["测试"],
            summary="测试真相。",
        ),
        timeline=[],
    )


def build_state(script: GameScript | None = None) -> GameState:
    """
    构造 GameState。
    """

    script_id = script.id if script else "test_investigation_script"
    return GameState(script_id=script_id)


def test_list_targets_returns_script_investigation_targets():
    """
    list_targets 应返回剧本中声明的所有调查对象。
    """

    script = build_script()
    service = InvestigationService(script)

    targets = service.list_targets()

    assert len(targets) == 5
    assert {target.id for target in targets} == {
        "target_body",
        "target_injector",
        "target_room",
        "target_hidden",
        "target_empty",
    }


def test_investigate_body_unlocks_configured_locked_clue():
    """
    调查尸体时，应解锁 target_body 配置的 LOCKED 线索。
    """

    script = build_script()
    state = build_state(script)
    service = InvestigationService(script)

    result = service.investigate(state, "target_body")

    assert result.target_id == "target_body"
    assert result.target_name == "尸体"
    assert result.target_type == "BODY"

    assert result.has_new_clues is True
    assert [clue.id for clue in result.newly_discovered_clues] == ["clue_body_mark"]
    assert result.already_discovered_clues == []
    assert result.skipped_hidden_clue_ids == []

    assert "clue_body_mark" in state.unlocked_clue_ids
    assert "发现 1 条新线索" in result.message


def test_repeated_investigation_does_not_unlock_duplicate_clue():
    """
    重复调查同一对象时，不应重复解锁同一线索。

    第一次调查：newly_discovered_clues 有线索。
    第二次调查：already_discovered_clues 有线索。
    """

    script = build_script()
    state = build_state(script)
    service = InvestigationService(script)

    first_result = service.investigate(state, "target_body")
    second_result = service.investigate(state, "target_body")

    assert [clue.id for clue in first_result.newly_discovered_clues] == [
        "clue_body_mark"
    ]

    assert second_result.newly_discovered_clues == []
    assert [clue.id for clue in second_result.already_discovered_clues] == [
        "clue_body_mark"
    ]

    assert state.unlocked_clue_ids == {"clue_body_mark"}
    assert "没有发现新线索" in second_result.message


def test_investigate_public_clue_is_already_known():
    """
    PUBLIC 线索从开局就可见。

    如果调查对象绑定了 PUBLIC 线索，
    服务应把它放入 already_discovered_clues，
    而不是 newly_discovered_clues。
    """

    script = build_script()
    state = build_state(script)
    service = InvestigationService(script)

    result = service.investigate(state, "target_room")

    assert result.newly_discovered_clues == []
    assert [clue.id for clue in result.already_discovered_clues] == [
        "clue_public_scene"
    ]

    # PUBLIC 线索不需要加入 unlocked_clue_ids。
    assert "clue_public_scene" not in state.unlocked_clue_ids


def test_investigate_unknown_target_should_raise():
    """
    调查不存在的 target_id 时，应抛出明确异常。
    """

    script = build_script()
    state = build_state(script)
    service = InvestigationService(script)

    with pytest.raises(
        InvestigationTargetNotFoundError,
        match="Unknown investigation_target_id",
    ):
        service.investigate(state, "target_not_exists")


def test_investigate_empty_target_returns_no_clues():
    """
    调查没有绑定线索的对象时，应返回空结果，不应报错。
    """

    script = build_script()
    state = build_state(script)
    service = InvestigationService(script)

    result = service.investigate(state, "target_empty")

    assert result.newly_discovered_clues == []
    assert result.already_discovered_clues == []
    assert result.skipped_hidden_clue_ids == []
    assert state.unlocked_clue_ids == set()
    assert "没有发现新的有效线索" in result.message


def test_investigate_should_not_unlock_hidden_clue():
    """
    HIDDEN 线索不能通过普通调查解锁。

    即使剧本误把 HIDDEN clue_id 放进 discoverable_clue_ids，
    InvestigationService 也必须跳过。
    """

    script = build_script()
    state = build_state(script)
    service = InvestigationService(script)

    result = service.investigate(state, "target_hidden")

    assert result.newly_discovered_clues == []
    assert result.already_discovered_clues == []
    assert result.skipped_hidden_clue_ids == ["clue_hidden_truth"]

    assert "clue_hidden_truth" not in state.unlocked_clue_ids
    assert "暂时没有发现可以确认的新线索" in result.message


def test_investigation_result_to_dict_should_not_expose_hidden_clue_content():
    """
    to_dict 可以导出 skipped_hidden_clue_ids，
    但不能暴露 HIDDEN 线索内容。
    """

    script = build_script()
    state = build_state(script)
    service = InvestigationService(script)

    result = service.investigate(state, "target_hidden")
    data = result.to_dict()

    assert data["target_id"] == "target_hidden"
    assert data["newly_discovered_clue_ids"] == []
    assert data["already_discovered_clue_ids"] == []
    assert data["skipped_hidden_clue_ids"] == ["clue_hidden_truth"]

    # 确保没有把隐藏线索标题或内容导出。
    assert "隐藏真相线索" not in str(data)
    assert "这条线索不应该通过普通调查暴露" not in str(data)