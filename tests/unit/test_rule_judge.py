from pathlib import Path

import pytest

from stery.application.game_runtime import GameRuntime
from stery.application.rule_judge import RuleJudge
from stery.application.script_loader import load_script
from stery.domain.state import FinalVote


PROJECT_ROOT = Path(__file__).resolve().parents[2]
SCRIPT_PATH = PROJECT_ROOT / "scripts" / "mansion_murder.json"


def build_judge() -> RuleJudge:
    script = load_script(SCRIPT_PATH)
    return RuleJudge(script)


def test_ensure_character_exists_success():
    judge = build_judge()

    judge.ensure_character_exists("npc_doctor")


def test_ensure_character_exists_failed():
    judge = build_judge()

    with pytest.raises(ValueError, match="Unknown character_id"):
        judge.ensure_character_exists("npc_not_exists")


def test_ensure_clues_exist_success():
    judge = build_judge()

    judge.ensure_clues_exist(
        [
            "clue_broken_glass",
            "clue_medicine_bottle",
        ]
    )


def test_ensure_clues_exist_failed():
    judge = build_judge()

    with pytest.raises(ValueError, match="Unknown clue_id"):
        judge.ensure_clues_exist(["clue_not_exists"])


def test_evaluate_final_vote_all_correct():
    judge = build_judge()

    vote = FinalVote(
        suspect_character_id="npc_doctor",
        motive="周医生被顾明远长期勒索。",
        method="将过量镇静剂混入红酒中。",
        key_evidence=[
            "clue_broken_glass",
            "clue_medicine_bottle",
            "clue_torn_letter",
        ],
    )

    result = judge.evaluate_final_vote(vote)

    assert result.is_correct is True
    assert result.matched_murderer is True
    assert result.score == 100
    assert set(result.matched_key_clue_ids) == {
        "clue_broken_glass",
        "clue_medicine_bottle",
        "clue_torn_letter",
    }


def test_evaluate_final_vote_wrong_murderer():
    judge = build_judge()

    vote = FinalVote(
        suspect_character_id="npc_butler",
        motive="管家不满顾明远变卖庄园。",
        method="使用备用钥匙进入书房作案。",
        key_evidence=[
            "clue_broken_glass",
            "clue_medicine_bottle",
            "clue_torn_letter",
        ],
    )

    result = judge.evaluate_final_vote(vote)

    assert result.is_correct is False
    assert result.matched_murderer is False
    assert result.score == 40


def test_evaluate_final_vote_partial_key_clues():
    judge = build_judge()

    vote = FinalVote(
        suspect_character_id="npc_doctor",
        motive="周医生被顾明远长期勒索。",
        method="将过量镇静剂混入红酒中。",
        key_evidence=[
            "clue_broken_glass",
        ],
    )

    result = judge.evaluate_final_vote(vote)

    assert result.is_correct is False
    assert result.matched_murderer is True
    assert result.score == 73
    assert result.matched_key_clue_ids == ["clue_broken_glass"]


def test_evaluate_final_vote_unknown_character_failed():
    judge = build_judge()

    vote = FinalVote(
        suspect_character_id="npc_not_exists",
        motive="测试",
        method="测试",
        key_evidence=["clue_broken_glass"],
    )

    with pytest.raises(ValueError, match="Unknown character_id"):
        judge.evaluate_final_vote(vote)


def test_evaluate_final_vote_unknown_clue_failed():
    judge = build_judge()

    vote = FinalVote(
        suspect_character_id="npc_doctor",
        motive="测试",
        method="测试",
        key_evidence=["clue_not_exists"],
    )

    with pytest.raises(ValueError, match="Unknown clue_id"):
        judge.evaluate_final_vote(vote)


def test_evaluate_final_vote_from_game_runtime_state():
    script = load_script(SCRIPT_PATH)
    runtime = GameRuntime(script)
    state = runtime.start()

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

    judge = RuleJudge(script)
    result = judge.evaluate_final_vote(state.final_vote)

    assert result.is_correct is True
    assert result.score == 100