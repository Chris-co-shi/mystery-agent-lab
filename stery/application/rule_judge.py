from pydantic import BaseModel, ConfigDict, Field

from stery.domain.models import GameScript
from stery.domain.state import FinalVote


class JudgeBaseModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class FinalVoteEvaluation(JudgeBaseModel):
    """
    最终推理评估结果。
    """

    is_correct: bool
    matched_murderer: bool
    matched_key_clue_ids: list[str] = Field(default_factory=list)
    score: int
    reason: str


class RuleJudge:
    """
    最小规则裁判。

    当前阶段不接 LLM，只做确定性规则判断：
    - 角色是否存在
    - 线索是否存在
    - 最终推理是否命中真相
    """

    def __init__(self, script: GameScript):
        self.script = script
        self._character_ids = {character.id for character in script.characters}
        self._clue_ids = {clue.id for clue in script.clues}

    def ensure_character_exists(self, character_id: str) -> None:
        if character_id not in self._character_ids:
            raise ValueError(f"Unknown character_id: {character_id}")

    def ensure_clues_exist(self, clue_ids: list[str]) -> None:
        for clue_id in clue_ids:
            if clue_id not in self._clue_ids:
                raise ValueError(f"Unknown clue_id: {clue_id}")

    def evaluate_final_vote(self, vote: FinalVote) -> FinalVoteEvaluation:
        """
        评估玩家最终推理。

        当前评分规则：
        - 凶手正确：60 分
        - 关键线索命中：共 40 分，按命中比例计算
        - 满分 100
        """
        self.ensure_character_exists(vote.suspect_character_id)
        self.ensure_clues_exist(vote.key_evidence)

        truth = self.script.truth

        matched_murderer = vote.suspect_character_id == truth.id

        truth_key_clue_ids = set(truth.key_clue_ids)
        submitted_key_clue_ids = set(vote.key_evidence)

        matched_key_clue_ids = sorted(
            truth_key_clue_ids.intersection(submitted_key_clue_ids)
        )

        murderer_score = 60 if matched_murderer else 0

        if truth_key_clue_ids:
            clue_score = int(40 * len(matched_key_clue_ids) / len(truth_key_clue_ids))
        else:
            clue_score = 0

        score = murderer_score + clue_score

        is_correct = matched_murderer and truth_key_clue_ids.issubset(
            submitted_key_clue_ids
        )

        reason = self._build_reason(
            matched_murderer=matched_murderer,
            matched_key_clue_ids=matched_key_clue_ids,
            truth_key_clue_ids=truth_key_clue_ids,
            score=score,
        )

        return FinalVoteEvaluation(
            is_correct=is_correct,
            matched_murderer=matched_murderer,
            matched_key_clue_ids=matched_key_clue_ids,
            score=score,
            reason=reason,
        )

    def _build_reason(
        self,
        matched_murderer: bool,
        matched_key_clue_ids: list[str],
        truth_key_clue_ids: set[str],
        score: int,
    ) -> str:
        if matched_murderer and len(matched_key_clue_ids) == len(truth_key_clue_ids):
            return f"推理正确，凶手和关键线索均命中，得分 {score}。"

        if matched_murderer:
            return (
                f"凶手判断正确，但关键线索不完整，"
                f"命中 {len(matched_key_clue_ids)}/{len(truth_key_clue_ids)}，"
                f"得分 {score}。"
            )

        return (
            f"凶手判断错误，关键线索命中 "
            f"{len(matched_key_clue_ids)}/{len(truth_key_clue_ids)}，"
            f"得分 {score}。"
        )