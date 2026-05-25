from pathlib import Path

import pytest

from stery.application.game_runtime import GameRuntime
from stery.application.script_loader import load_script
from stery.domain.enums import GamePhase


PROJECT_ROOT = Path(__file__).resolve().parents[2]
from stery.config.paths import MANSION_MURDER_SCRIPT

SCRIPT_PATH = MANSION_MURDER_SCRIPT


def build_runtime() -> GameRuntime:
    script = load_script(SCRIPT_PATH)
    return GameRuntime(script)


def test_start_game_success():
    runtime = build_runtime()

    state = runtime.start()

    assert state.script_id == runtime.script.id
    assert state.current_phase == GamePhase.BACKGROUND_INTRO
    assert state.current_round == 0
    assert state.is_finished is False
    assert "clue_broken_glass" in state.unlocked_clue_ids


def test_get_background_requires_game_started():
    runtime = build_runtime()

    with pytest.raises(RuntimeError, match="Game has not started"):
        runtime.get_background()


def test_get_background_success():
    runtime = build_runtime()
    runtime.start()

    background = runtime.get_background()

    assert "顾明远" in background
    assert "庄园" in background


def test_list_characters_requires_game_started():
    runtime = build_runtime()

    with pytest.raises(RuntimeError, match="Game has not started"):
        runtime.list_characters()


def test_list_characters_success():
    runtime = build_runtime()
    runtime.start()

    characters = runtime.list_characters()

    assert len(characters) == 3

    character_ids = {character.id for character in characters}

    assert character_ids == {
        "npc_butler",
        "npc_daughter",
        "npc_doctor",
    }


def test_list_available_clues_success():
    runtime = build_runtime()
    runtime.start()

    clues = runtime.list_available_clues()
    clue_ids = {clue.id for clue in clues}

    assert "clue_broken_glass" in clue_ids
    assert "clue_medicine_bottle" not in clue_ids
    assert "clue_torn_letter" not in clue_ids


def test_unlock_clue_success():
    runtime = build_runtime()
    runtime.start()

    runtime.unlock_clue("clue_medicine_bottle")

    clues = runtime.list_available_clues()
    clue_ids = {clue.id for clue in clues}

    assert "clue_medicine_bottle" in clue_ids


def test_unlock_unknown_clue_failed():
    runtime = build_runtime()
    runtime.start()

    with pytest.raises(ValueError, match="Unknown clue_id"):
        runtime.unlock_clue("clue_not_exists")


def test_record_question_requires_game_started():
    runtime = build_runtime()

    with pytest.raises(RuntimeError, match="Game has not started"):
        runtime.record_question(
            target_character_id="npc_butler",
            question="案发当晚你在哪里？",
        )


def test_record_question_success():
    runtime = build_runtime()
    state = runtime.start()

    runtime.record_question(
        target_character_id="npc_butler",
        question="案发当晚你在哪里？",
    )

    assert state.current_phase == GamePhase.FREE_QUESTION
    assert state.current_round == 1
    assert len(state.question_history) == 1

    question = state.question_history[0]

    assert question.target_character_id == "npc_butler"
    assert question.content == "案发当晚你在哪里？"


def test_record_question_unknown_character_failed():
    runtime = build_runtime()
    runtime.start()

    with pytest.raises(ValueError, match="Unknown character_id"):
        runtime.record_question(
            target_character_id="npc_not_exists",
            question="你是谁？",
        )


def test_record_question_round_limit_failed():
    runtime = build_runtime()
    state = runtime.start()

    state.current_round = runtime.script.rules.max_question_rounds

    with pytest.raises(ValueError, match="Question round limit exceeded"):
        runtime.record_question(
            target_character_id="npc_butler",
            question="还能继续问吗？",
        )


def test_submit_final_vote_requires_game_started():
    runtime = build_runtime()

    with pytest.raises(RuntimeError, match="Game has not started"):
        runtime.submit_final_vote(
            suspect_character_id="npc_doctor",
            motive="周医生被顾明远长期勒索。",
            method="将过量镇静剂混入红酒中。",
            key_evidence=["clue_broken_glass"],
        )


def test_submit_final_vote_success():
    runtime = build_runtime()
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

    assert state.current_phase == GamePhase.REVEAL_TRUTH
    assert state.final_vote is not None
    assert state.final_vote.suspect_character_id == "npc_doctor"
    assert "clue_medicine_bottle" in state.final_vote.key_evidence


def test_submit_final_vote_unknown_character_failed():
    runtime = build_runtime()
    runtime.start()

    with pytest.raises(ValueError, match="Unknown character_id"):
        runtime.submit_final_vote(
            suspect_character_id="npc_not_exists",
            motive="测试",
            method="测试",
            key_evidence=["clue_broken_glass"],
        )


def test_submit_final_vote_unknown_clue_failed():
    runtime = build_runtime()
    runtime.start()

    with pytest.raises(ValueError, match="Unknown clue_id"):
        runtime.submit_final_vote(
            suspect_character_id="npc_doctor",
            motive="测试",
            method="测试",
            key_evidence=["clue_not_exists"],
        )


def test_finish_game_requires_game_started():
    runtime = build_runtime()

    with pytest.raises(RuntimeError, match="Game has not started"):
        runtime.finish()


def test_finish_game_success():
    runtime = build_runtime()
    state = runtime.start()

    runtime.finish()

    assert state.current_phase == GamePhase.END
    assert state.is_finished is True