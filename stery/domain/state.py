from datetime import datetime, timezone
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field

from stery.domain.enums import GamePhase


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class RuntimeBaseModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class QuestionRecord(RuntimeBaseModel):
    question_id: str = Field(default_factory=lambda: uuid4().hex)
    target_character_id: str
    content: str
    created_at: datetime = Field(default_factory=utc_now)


class FinalVote(RuntimeBaseModel):
    suspect_character_id: str
    motive: str
    method: str
    key_evidence: list[str] = Field(default_factory=list)
    submitted_at: datetime = Field(default_factory=utc_now)


class NPCAnswerRecord(RuntimeBaseModel):
    answer_id: str = Field(default_factory=lambda: uuid4().hex)
    question_id: str
    target_character_id: str
    content: str
    created_at: datetime = Field(default_factory=utc_now)

class QAHistoryItem(BaseModel):
    target_character_id: str
    player_question: str
    npc_answer: str

class GameState(RuntimeBaseModel):
    script_id: str
    current_phase: GamePhase = GamePhase.START
    current_round: int = 0
    unlocked_clue_ids: set[str] = Field(default_factory=set)
    question_history: list[QuestionRecord] = Field(default_factory=list)
    answer_history: list[NPCAnswerRecord] = Field(default_factory=list)
    final_vote: FinalVote | None = None
    is_finished: bool = False
    qa_history: list[QAHistoryItem] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)

    def touch(self) -> None:
        self.updated_at = utc_now()

    def add_qa_history(
            self,
            target_character_id: str,
            player_question: str,
            npc_answer: str,
    ) -> None:
        self.qa_history.append(
            QAHistoryItem(
                target_character_id=target_character_id,
                player_question=player_question,
                npc_answer=npc_answer,
            )
        )