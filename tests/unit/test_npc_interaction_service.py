from pathlib import Path

import pytest

from stery.application.game_runtime import GameRuntime
from stery.application.npc_interaction_service import NPCInteractionService
from stery.application.script_loader import load_script
from stery.domain.state import GameState
from stery.script_repository import LocalFileScriptRepository

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SCRIPT_PATH = "mansion_murder"

script = LocalFileScriptRepository().get_script(SCRIPT_PATH)


class FakeNPCAgent:
    def __init__(self, answer_text: str = "我当时只是在走廊巡查。"):
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


def build_runtime() -> GameRuntime:
    runtime = GameRuntime(script)
    runtime.start()
    return runtime


def test_ask_npc_success_records_question_and_answer():
    runtime = build_runtime()
    fake_agent = FakeNPCAgent("我当时只是在走廊巡查。")
    service = NPCInteractionService(runtime=runtime, npc_agent=fake_agent)

    result = service.ask_npc(
        target_character_id="npc_butler",
        question="案发当晚你在哪里？",
    )

    state = runtime.state

    assert state is not None
    assert len(state.question_history) == 1
    assert len(state.answer_history) == 1

    question = state.question_history[0]
    answer = state.answer_history[0]

    assert result.question_id == question.question_id
    assert result.answer_id == answer.answer_id
    assert result.target_character_id == "npc_butler"
    assert result.player_question == "案发当晚你在哪里？"
    assert result.npc_answer == "我当时只是在走廊巡查。"

    assert answer.question_id == question.question_id
    assert answer.target_character_id == "npc_butler"
    assert answer.content == "我当时只是在走廊巡查。"


def test_ask_npc_calls_agent_with_state_and_question():
    runtime = build_runtime()
    fake_agent = FakeNPCAgent()
    service = NPCInteractionService(runtime=runtime, npc_agent=fake_agent)

    service.ask_npc(
        target_character_id="npc_butler",
        question="案发当晚你在哪里？",
    )

    assert len(fake_agent.calls) == 1

    call = fake_agent.calls[0]

    assert call["state"] is runtime.state
    assert call["target_character_id"] == "npc_butler"
    assert call["player_question"] == "案发当晚你在哪里？"


def test_ask_npc_requires_game_started():
    runtime = GameRuntime(script)
    fake_agent = FakeNPCAgent()
    service = NPCInteractionService(runtime=runtime, npc_agent=fake_agent)

    with pytest.raises(RuntimeError, match="Game has not started"):
        service.ask_npc(
            target_character_id="npc_butler",
            question="案发当晚你在哪里？",
        )

    assert len(fake_agent.calls) == 0


def test_ask_npc_unknown_character_failed():
    runtime = build_runtime()
    fake_agent = FakeNPCAgent()
    service = NPCInteractionService(runtime=runtime, npc_agent=fake_agent)

    with pytest.raises(ValueError, match="Unknown character_id"):
        service.ask_npc(
            target_character_id="npc_not_exists",
            question="你是谁？",
        )

    assert len(fake_agent.calls) == 0


def test_ask_npc_respects_question_round_limit():
    runtime = build_runtime()
    fake_agent = FakeNPCAgent()
    service = NPCInteractionService(runtime=runtime, npc_agent=fake_agent)

    assert runtime.state is not None
    runtime.state.current_round = runtime.script.rules.max_question_rounds

    with pytest.raises(ValueError, match="Question round limit exceeded"):
        service.ask_npc(
            target_character_id="npc_butler",
            question="还能继续问吗？",
        )

    assert len(fake_agent.calls) == 0