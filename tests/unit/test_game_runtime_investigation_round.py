import pytest

from stery.application.game_runtime import GameRuntime
from stery.domain.enums import InvestigationRoundStatus
from stery.script_repository import LocalFileScriptRepository


SCRIPT_ID = "snow_inn_murder"


def build_runtime() -> GameRuntime:
    script = LocalFileScriptRepository().get_script(SCRIPT_ID)
    runtime = GameRuntime(script)
    runtime.start()
    return runtime


def test_start_should_create_first_open_investigation_round():
    runtime = build_runtime()

    state = runtime.state

    assert state is not None
    assert state.active_round_id is not None
    assert len(state.investigation_rounds) == 1

    first_round = state.investigation_rounds[0]

    assert first_round.round_no == 1
    assert first_round.status == InvestigationRoundStatus.OPEN
    assert first_round.closed_at is None
    assert first_round.question_ids == []
    assert state.active_round_id == first_round.round_id


def test_record_question_should_bind_question_to_active_round():
    runtime = build_runtime()

    runtime.record_question(
        target_character_id="npc_pharmacist",
        question="你是谁？",
    )

    state = runtime.state

    assert state is not None
    assert len(state.question_history) == 1
    assert len(state.investigation_rounds) == 1

    question = state.question_history[0]
    active_round = state.investigation_rounds[0]

    assert active_round.status == InvestigationRoundStatus.OPEN
    assert active_round.question_ids == [question.question_id]
    assert question.target_character_id == "npc_pharmacist"
    assert question.content == "你是谁？"


def test_record_multiple_questions_should_bind_all_to_same_active_round():
    runtime = build_runtime()

    runtime.record_question(
        target_character_id="npc_pharmacist",
        question="你是谁？",
    )
    runtime.record_question(
        target_character_id="npc_photographer",
        question="你在这里干什么？",
    )

    state = runtime.state

    assert state is not None
    assert len(state.question_history) == 2
    assert len(state.investigation_rounds) == 1

    first_question = state.question_history[0]
    second_question = state.question_history[1]
    active_round = state.investigation_rounds[0]

    assert active_round.status == InvestigationRoundStatus.OPEN
    assert active_round.question_ids == [
        first_question.question_id,
        second_question.question_id,
    ]


def test_close_current_round_should_close_old_round_and_open_next_round():
    runtime = build_runtime()

    runtime.record_question(
        target_character_id="npc_pharmacist",
        question="你是谁？",
    )

    state_before_close = runtime.state

    assert state_before_close is not None
    old_active_round_id = state_before_close.active_round_id

    runtime.close_current_round()

    state = runtime.state

    assert state is not None
    assert len(state.investigation_rounds) == 2
    assert state.active_round_id is not None
    assert state.active_round_id != old_active_round_id

    closed_round = state.investigation_rounds[0]
    new_round = state.investigation_rounds[1]

    assert closed_round.round_id == old_active_round_id
    assert closed_round.round_no == 1
    assert closed_round.status == InvestigationRoundStatus.CLOSED
    assert closed_round.closed_at is not None
    assert len(closed_round.question_ids) == 1

    assert new_round.round_no == 2
    assert new_round.status == InvestigationRoundStatus.OPEN
    assert new_round.closed_at is None
    assert new_round.question_ids == []
    assert state.active_round_id == new_round.round_id


def test_record_question_after_close_round_should_bind_to_new_active_round():
    runtime = build_runtime()

    runtime.record_question(
        target_character_id="npc_pharmacist",
        question="你是谁？",
    )

    runtime.close_current_round()

    runtime.record_question(
        target_character_id="npc_photographer",
        question="你在这里干什么？",
    )

    state = runtime.state

    assert state is not None
    assert len(state.question_history) == 2
    assert len(state.investigation_rounds) == 2

    first_question = state.question_history[0]
    second_question = state.question_history[1]

    first_round = state.investigation_rounds[0]
    second_round = state.investigation_rounds[1]

    assert first_round.status == InvestigationRoundStatus.CLOSED
    assert first_round.question_ids == [first_question.question_id]

    assert second_round.status == InvestigationRoundStatus.OPEN
    assert second_round.question_ids == [second_question.question_id]
    assert state.active_round_id == second_round.round_id


def test_close_current_round_should_fail_when_game_not_started():
    script = LocalFileScriptRepository().get_script(SCRIPT_ID)
    runtime = GameRuntime(script)

    with pytest.raises(RuntimeError, match="Game has not started"):
        runtime.close_current_round()


def test_close_current_round_should_fail_when_game_finished():
    runtime = build_runtime()

    runtime.finish()

    with pytest.raises(ValueError, match="Game has already finished"):
        runtime.close_current_round()


def test_record_question_should_fail_when_no_active_round():
    runtime = build_runtime()

    assert runtime.state is not None
    runtime.state.active_round_id = None

    with pytest.raises(RuntimeError, match="No active investigation round"):
        runtime.record_question(
            target_character_id="npc_pharmacist",
            question="你是谁？",
        )