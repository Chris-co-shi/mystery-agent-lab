from typing import Protocol

from pydantic import BaseModel, ConfigDict

from stery.application.game_runtime import GameRuntime
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
    model_config = ConfigDict(extra="forbid")

    question_id: str
    answer_id: str
    target_character_id: str
    player_question: str
    npc_answer: str


class NPCInteractionService:
    """
    NPC 交互应用服务。

    职责：
    - 记录玩家问题
    - 调用 NPC Agent 生成回答
    - 记录 NPC 回答
    - 返回本轮交互结果

    不负责：
    - Prompt 构造
    - LLM 调用细节
    - 线索解锁
    - 最终推理判断
    """

    def __init__(
        self,
        runtime: GameRuntime,
        npc_agent: NPCResponder,
    ):
        self.runtime = runtime
        self.npc_agent = npc_agent

    def ask_npc(
        self,
        target_character_id: str,
        question: str,
    ) -> NPCInteractionResult:
        state = self.runtime.record_question(
            target_character_id=target_character_id,
            question=question,
        )

        question_record = state.question_history[-1]

        npc_answer = self.npc_agent.answer(
            state=state,
            target_character_id=target_character_id,
            player_question=question,
        )

        state = self.runtime.record_npc_answer(
            target_character_id=target_character_id,
            question_id=question_record.question_id,
            answer=npc_answer,
        )

        answer_record = state.answer_history[-1]

        return NPCInteractionResult(
            question_id=question_record.question_id,
            answer_id=answer_record.answer_id,
            target_character_id=target_character_id,
            player_question=question,
            npc_answer=npc_answer,
        )