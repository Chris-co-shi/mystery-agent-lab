# tests/unit/test_known_info_search_service.py
from stery.case.known_info_search_service import KnownInfoSearchService
from stery.domain import ClueVisibility, GamePhase
from stery.domain.models import Character, Clue, GameRules, GameScript, Truth
from stery.domain.state import GameState


def build_script() -> GameScript:
    """
    构造已知信息检索测试剧本。

    核心场景：
    - PUBLIC 线索可以被搜索到
    - LOCKED 未解锁线索不能被搜索到
    - LOCKED 已解锁线索可以被搜索到
    - HIDDEN 线索不能被搜索到
    """

    return GameScript(
        id="known_info_search_script",
        title="已知信息检索测试剧本",
        version="v0.2.0",
        background="测试 /search 降级为已知信息检索。",
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
                content="书房中有破碎红酒杯。",
                visibility=ClueVisibility.PUBLIC,
                unlock_phase=GamePhase.START,
                search_keywords=["书房", "红酒杯"],
            ),
            Clue(
                id="clue_locked_injector",
                title="异常注入器",
                content="注入器批号与登记记录不一致。",
                visibility=ClueVisibility.LOCKED,
                unlock_phase=GamePhase.START,
                search_keywords=["注入器", "批号"],
            ),
            Clue(
                id="clue_hidden_truth",
                title="隐藏真相",
                content="这条线索不应通过 search 出现。",
                visibility=ClueVisibility.HIDDEN,
                unlock_phase=GamePhase.START,
                search_keywords=["隐藏"],
            ),
        ],
        truth=Truth(
            id="npc_doctor",
            murderer_id="npc_doctor",
            motive="测试动机",
            method="测试手法",
            key_clue_ids=["clue_locked_injector"],
            motive_keywords=["测试"],
            method_keywords=["测试"],
            summary="测试真相。",
        ),
        timeline=[],
    )


def build_state(script: GameScript) -> GameState:
    return GameState(script_id=script.id)


def test_search_should_find_public_clue():
    """
    PUBLIC 线索从开局就已知，所以可以被 /search 检索到。
    """

    script = build_script()
    state = build_state(script)

    result = KnownInfoSearchService(script).search(
        state=state,
        keyword="红酒杯",
    )

    assert result.has_matches is True
    assert [match.source_id for match in result.matches] == ["clue_public_scene"]


def test_search_should_not_unlock_or_find_locked_unknown_clue():
    """
    LOCKED 但未解锁的线索不能被 /search 找到。

    这就是 TASK-009 的核心目标：
    /search 不再作为线索解锁入口。
    """

    script = build_script()
    state = build_state(script)

    result = KnownInfoSearchService(script).search(
        state=state,
        keyword="注入器",
    )

    assert result.has_matches is False
    assert state.unlocked_clue_ids == set()


def test_search_should_find_unlocked_locked_clue():
    """
    LOCKED 线索如果已经通过 /investigate 解锁，
    就可以被 /search 检索到。
    """

    script = build_script()
    state = build_state(script)
    state.unlocked_clue_ids.add("clue_locked_injector")

    result = KnownInfoSearchService(script).search(
        state=state,
        keyword="注入器",
    )

    assert result.has_matches is True
    assert [match.source_id for match in result.matches] == ["clue_locked_injector"]


def test_search_should_not_find_hidden_clue_even_if_keyword_matches():
    """
    HIDDEN 线索永远不能通过普通 /search 暴露。
    """

    script = build_script()
    state = build_state(script)

    result = KnownInfoSearchService(script).search(
        state=state,
        keyword="隐藏",
    )

    assert result.has_matches is False
    assert "clue_hidden_truth" not in [match.source_id for match in result.matches]


def test_search_empty_keyword_should_return_empty_result():
    script = build_script()
    state = build_state(script)

    result = KnownInfoSearchService(script).search(
        state=state,
        keyword="   ",
    )

    assert result.has_matches is False
    assert result.message == "搜索关键词不能为空。"