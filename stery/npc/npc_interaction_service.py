from collections.abc import Callable
from typing import Protocol

from pydantic import BaseModel

from stery.npc.npc_guardrail import NpcGuardrail
from stery.domain.state import GameState


class NPCResponder(Protocol):
    """
    NPC 回答器协议。

    真实实现可以是 NPCAgent。
    测试中可以用 FakeNPCAgent。
    """

    def answer(
            self,
            state: GameState,
            target_character_id: str,
            player_question: str,
    ) -> str:
        ...


class NPCInteractionResult(BaseModel):
    target_character_id: str
    question: str
    npc_answer: str


def _build_guarded_question(
        question: str,
        guardrail_instruction: str,
) -> str:
    if not guardrail_instruction:
        return question

    return (
        f"{question}\n\n"
        f"{guardrail_instruction}\n\n"
        "请严格遵守以上 NPC 回答边界。"
    )


def _touch_state(state: GameState) -> None:
    state.touch()


class NPCInteractionService:
    """
    NPC 交互应用服务。

    职责：
    - 接收玩家问题
    - 调用 NPC Guardrail 判断回答模式
    - 调用 NPCResponder 生成 NPC 回答
    - 对 NPC 回答做轻量兜底检查
    - 返回本轮交互结果

    不负责：
    - Prompt 底层构造细节
    - LLM Provider 调用细节
    - 线索解锁
    - 最终推理判断
    """

    def __init__(
            self,
            state_provider: Callable[[], GameState | None],
            record_question: Callable[[str, str], GameState],
            record_npc_answer: Callable[[str, str], GameState],
            responder: NPCResponder,
            npc_guardrail: NpcGuardrail | None = None,
    ):
        """
        state_provider:
            返回当前 GameState。

            推荐用法：
                NPCInteractionService(
                    state_provider=lambda: runtime.state,
                    responder=npc_agent,
                )

            这样可以避免 service 初始化时 runtime.state 还是 None 的问题。

        responder:
            NPC 回答器，例如 NPCAgent。
        """
        self.state_provider = state_provider
        self.responder = responder
        self.npc_guardrail = npc_guardrail or NpcGuardrail()
        self.record_question = record_question
        self.record_npc_answer = record_npc_answer

    def ask_npc(
            self,
            target_character_id: str,
            question: str,
    ) -> NPCInteractionResult:
        original_question = question.strip()

        if not target_character_id.strip():
            return NPCInteractionResult(
                target_character_id=target_character_id,
                question=original_question,
                npc_answer="你还没有说明要询问谁。",
            )

        if not original_question:
            return NPCInteractionResult(
                target_character_id=target_character_id,
                question=original_question,
                npc_answer="你还没有提出问题。",
            )

        state = self._require_state()
        self.record_question(
            target_character_id,
            original_question,
        )
        guardrail_result = self.npc_guardrail.check_question(
            question=original_question,
        )

        if not guardrail_result.should_call_llm:
            answer = (
                    guardrail_result.fallback_answer
                    or self.npc_guardrail.build_llm_error_fallback()
            )
            self.record_npc_answer(
                target_character_id,
                answer,
            )
            _touch_state(state)

            return NPCInteractionResult(
                target_character_id=target_character_id,
                question=original_question,
                npc_answer=answer,
            )

        guarded_question = _build_guarded_question(
            question=original_question,
            guardrail_instruction=guardrail_result.prompt_instruction,
        )

        try:
            raw_answer = self.responder.answer(
                state=state,
                target_character_id=target_character_id,
                player_question=guarded_question,
            )

            safe_answer = self.npc_guardrail.sanitize_answer(
                question=original_question,
                answer=raw_answer,
            )
            self.record_npc_answer(
                target_character_id,
                safe_answer
            )
        except Exception as e:
            print(f"ask error:{e}")
            safe_answer = self.npc_guardrail.build_llm_error_fallback()
            self.record_npc_answer(
                target_character_id,
                safe_answer
            )

        _touch_state(state)

        return NPCInteractionResult(
            target_character_id=target_character_id,
            question=original_question,
            npc_answer=safe_answer,
        )

    def _require_state(self) -> GameState:
        state = self.state_provider()

        if state is None:
            raise RuntimeError("Game state is not initialized. Did you call runtime.start()?")

        return state
