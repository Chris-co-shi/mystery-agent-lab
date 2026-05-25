from pathlib import Path

from stery.application.clue_search_service import ClueSearchService
from stery.application.game_runtime import GameRuntime
from stery.application.npc_interaction_service import NPCInteractionService
from stery.application.rule_judge import RuleJudge
from stery.application.script_loader import load_script
from stery.domain.state import GameState


PROJECT_ROOT = Path(__file__).resolve().parents[2]
from stery.config.paths import MANSION_MURDER_SCRIPT

SCRIPT_PATH = MANSION_MURDER_SCRIPT


class FakeNPCAgent:
    def __init__(self, answer_text: str = "我当时只是在走廊巡查，后来看到书房门虚掩着，但没有进去。"):
        self.answer_text = answer_text
        self.calls: list[dict] = []

    def answer(
        self,
        state: GameState,
        target_character_id: str,
        player_question: str,
    ) -> str:
        self.calls.append(
            {
                "state": state,
                "target_character_id": target_character_id,
                "player_question": player_question,
            }
        )
        return self.answer_text


def test_single_player_cli_game_flow_success():
    script = load_script(SCRIPT_PATH)

    runtime = GameRuntime(script)
    state = runtime.start()

    assert state is not None
    assert state.script_id == "mansion_murder_001"
    assert state.is_finished is False

    clue_search_service = ClueSearchService(script)
    npc_agent = FakeNPCAgent()
    npc_interaction_service = NPCInteractionService(
        runtime=runtime,
        npc_agent=npc_agent,
    )
    rule_judge = RuleJudge(script)

    # 1. 初始公开线索可见
    initial_clues = runtime.list_available_clues()
    initial_clue_ids = {clue.id for clue in initial_clues}

    assert "clue_broken_glass" in initial_clue_ids
    assert "clue_medicine_bottle" not in initial_clue_ids
    assert "clue_torn_letter" not in initial_clue_ids

    # 2. 搜索“抽屉”，解锁药瓶线索
    medicine_result = clue_search_service.search(state, "抽屉")

    assert len(medicine_result.unlocked_clues) == 1
    assert medicine_result.unlocked_clues[0].id == "clue_medicine_bottle"
    assert "clue_medicine_bottle" in state.unlocked_clue_ids

    # 3. 搜索“垃圾桶”，解锁勒索信线索
    letter_result = clue_search_service.search(state, "垃圾桶")

    assert len(letter_result.unlocked_clues) == 1
    assert letter_result.unlocked_clues[0].id == "clue_torn_letter"
    assert "clue_torn_letter" in state.unlocked_clue_ids

    # 4. 当前可见线索包含已解锁线索
    available_clues = runtime.list_available_clues()
    available_clue_ids = {clue.id for clue in available_clues}

    assert "clue_broken_glass" in available_clue_ids
    assert "clue_medicine_bottle" in available_clue_ids
    assert "clue_torn_letter" in available_clue_ids

    # 5. 询问 NPC，并记录问答
    interaction_result = npc_interaction_service.ask_npc(
        target_character_id="npc_butler",
        question="案发当晚 22 点左右，你在哪里？",
    )

    assert interaction_result.target_character_id == "npc_butler"
    assert interaction_result.player_question == "案发当晚 22 点左右，你在哪里？"
    assert interaction_result.npc_answer

    assert len(state.question_history) == 1
    assert len(state.answer_history) == 1
    assert state.answer_history[0].question_id == state.question_history[0].question_id

    assert len(npc_agent.calls) == 1
    assert npc_agent.calls[0]["target_character_id"] == "npc_butler"

    # 6. 提交最终推理
    runtime.submit_final_vote(
        suspect_character_id="npc_doctor",
        motive="周医生被顾明远长期勒索。",
        method="将过量镇静剂混入红酒中。",
        key_evidence=[
            "clue_broken_glass",
            "clue_medicine_bottle",
            "clue_torn_letter",
        ],
    )

    assert state.final_vote is not None

    # 7. RuleJudge 评分
    evaluation = rule_judge.evaluate_final_vote(state.final_vote)

    assert evaluation.is_correct is True
    assert evaluation.matched_murderer is True
    assert evaluation.score == 100
    assert set(evaluation.matched_key_clue_ids) == {
        "clue_broken_glass",
        "clue_medicine_bottle",
        "clue_torn_letter",
    }

    # 8. 结束游戏
    runtime.finish()

    assert state.is_finished is True