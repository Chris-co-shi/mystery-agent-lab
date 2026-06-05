# tests/unit/test_case_notebook_service.py

from stery.case.case_notebook_service import CaseNotebookService
from stery.domain import ClueVisibility, GamePhase
from stery.domain.case_record import CaseRecord
from stery.domain.enums import CaseActionType
from stery.domain.models import Character, Clue, GameRules, GameScript, Truth
from stery.domain.state import GameState


def build_script() -> GameScript:
    """
    构造案件笔记本测试剧本。

    只验证 CaseNotebookService，不测试 CLI。
    """

    return GameScript(
        id="case_notebook_script",
        title="案件笔记本测试剧本",
        version="v0.2.0",
        background="测试案件笔记本。",
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
                is_key_clue=False,
            ),
            Clue(
                id="clue_injector",
                title="异常注入器",
                content="注入器批号与登记记录不一致。",
                visibility=ClueVisibility.LOCKED,
                unlock_phase=GamePhase.START,
                is_key_clue=True,
                reasoning_tags=["METHOD", "KEY_EVIDENCE"],
            ),
            Clue(
                id="clue_hidden_truth",
                title="隐藏真相",
                content="不应该进入案件笔记本。",
                visibility=ClueVisibility.HIDDEN,
                unlock_phase=GamePhase.START,
                is_key_clue=True,
            ),
        ],
        truth=Truth(
            id="npc_doctor",
            murderer_id="npc_doctor",
            motive="测试动机",
            method="测试手法",
            key_clue_ids=["clue_injector"],
            motive_keywords=["测试"],
            method_keywords=["测试"],
            summary="测试真相。",
        ),
        timeline=[],
    )


def build_state(script: GameScript) -> GameState:
    return GameState(script_id=script.id)


def test_case_notebook_should_include_public_and_unlocked_clues():
    """
    Notebook 应包含：
    - PUBLIC 线索
    - 已解锁 LOCKED 线索

    不应包含：
    - 未解锁 LOCKED 线索
    - HIDDEN 线索
    """

    script = build_script()
    state = build_state(script)
    state.unlocked_clue_ids.add("clue_injector")

    notebook = CaseNotebookService(script).build(state)

    clue_ids = [clue.clue_id for clue in notebook.discovered_clues]

    assert clue_ids == ["clue_public_scene", "clue_injector"]
    assert "clue_hidden_truth" not in clue_ids


def test_case_notebook_should_include_evidence_candidates_from_key_clues():
    """
    当前 MVP 中，证据候选来自已发现线索里 is_key_clue=True 的线索。
    """

    script = build_script()
    state = build_state(script)
    state.unlocked_clue_ids.add("clue_injector")

    notebook = CaseNotebookService(script).build(state)

    candidate_ids = [clue.clue_id for clue in notebook.evidence_candidates]

    assert candidate_ids == ["clue_injector"]


def test_case_notebook_should_include_investigated_targets_from_case_records():
    """
    Notebook 应从 case_records 中整理已调查对象。
    """

    script = build_script()
    state = build_state(script)

    state.case_records.append(
        CaseRecord(
            action_type=CaseActionType.INVESTIGATE,
            title="调查：注入器",
            summary="玩家调查了：注入器；发现 1 条新线索。",
            metadata={
                "target_id": "target_injector",
                "target_name": "注入器",
                "target_type": "ITEM",
                "newly_discovered_clue_ids": ["clue_injector"],
                "already_discovered_clue_ids": [],
                "skipped_hidden_clue_ids": [],
            },
        )
    )

    notebook = CaseNotebookService(script).build(state)

    assert len(notebook.investigated_targets) == 1

    target = notebook.investigated_targets[0]

    assert target.target_id == "target_injector"
    assert target.target_name == "注入器"
    assert target.target_type == "ITEM"
    assert target.newly_discovered_clue_ids == ["clue_injector"]


def test_case_notebook_to_dict_should_be_serializable():
    """
    Notebook.to_dict() 应输出可用于 JSON / Markdown 导出的结构。
    """

    script = build_script()
    state = build_state(script)
    state.unlocked_clue_ids.add("clue_injector")

    notebook = CaseNotebookService(script).build(state)
    data = notebook.to_dict()

    assert "discovered_clues" in data
    assert "investigated_targets" in data
    assert "npc_questions" in data
    assert "evidence_candidates" in data

    assert data["discovered_clues"][0]["clue_id"] == "clue_public_scene"