from pathlib import Path
from types import SimpleNamespace

import pytest

from stery.application.game_runtime import GameRuntime
from stery.application.npc_interaction_service import NPCInteractionService
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

class FakeNPCResponder:
    def __init__(self, answer_text: str = "我当时一直在前台。"):
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


class FakeNpcGuardrail:
    def check_question(self, question: str):
        return SimpleNamespace(
            should_call_llm=True,
            prompt_instruction="",
            fallback_answer=None,
        )

    def sanitize_answer(self, question: str, answer: str) -> str:
        return answer

    def build_llm_error_fallback(self) -> str:
        return "NPC 暂时无法回答。"

def build_runtime() -> GameRuntime:
    runtime = GameRuntime(script)
    runtime.start()
    return runtime


def test_ask_npc_success_records_question_and_answer():
    runtime = build_runtime()
    fake_agent = FakeNPCAgent("我当时只是在走廊巡查。")
    service = NPCInteractionService(
        state_provider=lambda: runtime.state,
        responder=fake_agent,
        record_npc_answer=runtime.record_npc_answer,
        record_question=runtime.record_question
    )

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

    assert result.question == question.content
    assert result.npc_answer == answer.content
    assert answer.question_id == question.question_id
    assert result.target_character_id == "npc_butler"

    assert answer.target_character_id == "npc_butler"
    assert answer.content == "我当时只是在走廊巡查。"


def test_ask_npc_calls_agent_with_state_and_question():
    runtime = build_runtime()
    fake_agent = FakeNPCAgent()
    service = NPCInteractionService(
        state_provider=lambda: runtime.state,
        responder=fake_agent,
        record_npc_answer=runtime.record_npc_answer,
        record_question=runtime.record_question
    )

    service.ask_npc(
        target_character_id="npc_butler",
        question="案发当晚你在哪里？",
    )

    assert len(fake_agent.calls) == 1

    call = fake_agent.calls[0]

    assert call["state"] is runtime.state
    assert call["target_character_id"] == "npc_butler"
    assert "案发当晚你在哪里？" in call["player_question"]


def test_ask_npc_requires_game_started():
    runtime = GameRuntime(script)
    fake_agent = FakeNPCAgent()
    service = NPCInteractionService(
        state_provider=lambda: runtime.state,
        responder=fake_agent,
        record_npc_answer=runtime.record_npc_answer,
        record_question=runtime.record_question
    )

    with pytest.raises(RuntimeError, match="runtime.start"):
        service.ask_npc(
            target_character_id="npc_butler",
            question="案发当晚你在哪里？",
        )

    assert len(fake_agent.calls) == 0


def test_ask_npc_unknown_character_failed():
    runtime = build_runtime()
    fake_agent = FakeNPCAgent()
    service = NPCInteractionService(
        state_provider=lambda: runtime.state,
        responder=fake_agent,
        record_npc_answer=runtime.record_npc_answer,
        record_question=runtime.record_question
    )

    with pytest.raises(ValueError, match="Unknown character_id"):
        service.ask_npc(
            target_character_id="npc_not_exists",
            question="你是谁？",
        )

    assert len(fake_agent.calls) == 0
