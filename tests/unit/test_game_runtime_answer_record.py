from pathlib import Path

import pytest

from stery.application.game_runtime import GameRuntime
from stery.application.script_loader import load_script


PROJECT_ROOT = Path(__file__).resolve().parents[2]
from stery.config.paths import MANSION_MURDER_SCRIPT

SCRIPT_PATH = MANSION_MURDER_SCRIPT


def build_runtime() -> GameRuntime:
    script = load_script(SCRIPT_PATH)
    runtime = GameRuntime(script)
    runtime.start()
    return runtime


def test_record_npc_answer_success():
    runtime = build_runtime()
    state = runtime.state

    runtime.record_question(
        target_character_id="npc_butler",
        question="案发当晚你在哪里？",
    )

    runtime.record_npc_answer(
        target_character_id="npc_butler",
        answer="我当时只是在走廊巡查。",
    )

    assert state is not None
    assert len(state.question_history) == 1
    assert len(state.answer_history) == 1

    question = state.question_history[0]
    answer = state.answer_history[0]

    assert answer.question_id == question.question_id
    assert answer.target_character_id == "npc_butler"
    assert answer.content == "我当时只是在走廊巡查。"


def test_record_npc_answer_requires_existing_question():
    runtime = build_runtime()

    with pytest.raises(ValueError, match="No question found"):
        runtime.record_npc_answer(
            target_character_id="npc_butler",
            answer="我当时只是在走廊巡查。",
        )


def test_record_npc_answer_unknown_character_failed():
    runtime = build_runtime()

    with pytest.raises(ValueError, match="Unknown character_id"):
        runtime.record_npc_answer(
            target_character_id="npc_not_exists",
            answer="测试回答",
        )


def test_record_npc_answer_unknown_question_id_failed():
    runtime = build_runtime()

    runtime.record_question(
        target_character_id="npc_butler",
        question="案发当晚你在哪里？",
    )

    with pytest.raises(ValueError, match="Unknown question_id"):
        runtime.record_npc_answer(
            target_character_id="npc_butler",
            question_id="question_not_exists",
            answer="测试回答",
        )


def test_record_npc_answer_question_target_mismatch_failed():
    runtime = build_runtime()
    state = runtime.state

    runtime.record_question(
        target_character_id="npc_butler",
        question="案发当晚你在哪里？",
    )

    assert state is not None
    question_id = state.question_history[0].question_id

    with pytest.raises(ValueError, match="Question target mismatch"):
        runtime.record_npc_answer(
            target_character_id="npc_doctor",
            question_id=question_id,
            answer="测试回答",
        )