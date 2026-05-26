from datetime import datetime, timezone
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field

from stery.domain.enums import GamePhase, InvestigationRoundStatus


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


class InvestigationRound(RuntimeBaseModel):
    round_id: str = Field(default_factory=lambda: uuid4().hex)
    round_no: int
    status: InvestigationRoundStatus = InvestigationRoundStatus.OPEN
    question_ids: list[str] = Field(default_factory=list)
    started_at: datetime | None = None
    closed_at: datetime | None = None


class GameState(RuntimeBaseModel):
    script_id: str
    current_phase: GamePhase = GamePhase.START
    # 回答次数
    current_round: int = 0
    unlocked_clue_ids: set[str] = Field(default_factory=set)
    question_history: list[QuestionRecord] = Field(default_factory=list)
    answer_history: list[NPCAnswerRecord] = Field(default_factory=list)
    final_vote: FinalVote | None = None
    is_finished: bool = False
    # 激活轮次Id
    active_round_id: str | None = None
    investigation_rounds: list[InvestigationRound] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)

    def touch(self) -> None:
        self.updated_at = utc_now()
