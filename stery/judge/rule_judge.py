from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from stery.domain.models import GameScript
from stery.domain.state import FinalVote
from stery.judge.scoring import ScoringConfig, build_score_breakdown


class JudgeBaseModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class FinalVoteEvaluation(JudgeBaseModel):
    """
    最终推理评估结果。

    V0.2.0 增加：
    - max_score：满分，不再只隐含为 100。
    - score_breakdown：凶手、证据、动机、手法的可解释评分结果。

    保留旧字段：
    - is_correct
    - matched_murderer
    - matched_key_clue_ids
    - score
    - reason

    这样可以降低对现有调用方和旧测试的破坏。
    """

    # 是否完全正确。
    #
    # V0.2.0 后，“完全正确”表示四个评分部分都拿满分。
    # 例如：凶手、关键证据、动机、手法都正确。
    is_correct: bool
    # 凶手是否命中。
    matched_murderer: bool
    # 命中的关键线索 ID。
    matched_key_clue_ids: list[str] = Field(default_factory=list)
    # 实际得分。
    score: int
    # 满分。
    max_score: int = 100
    # 简短文字说明。
    #
    # 详细说明保存在 score_breakdown 中。
    reason: str
    # V0.2.0 新增：详细评分拆解。
    #
    # 使用 dict 而不是直接嵌套 ScoreBreakdown：
    # - 降低 rule_judge.py 对 scoring.py 内部 dataclass 的耦合。
    # - 方便 JSON / Markdown 导出。
    # - 方便后续前端展示。
    score_breakdown: dict[str, Any] = Field(default_factory=dict)


def _build_reason(score_breakdown: Any) -> str:
    """
    构建简短评分说明。

    详细解释已经在 score_breakdown 中保存。
    reason 只保留摘要，兼容旧 UI、旧导出和旧测试。
    """

    return (
        f"总分 {score_breakdown.total_score}/{score_breakdown.max_score}。"
        f"凶手 {score_breakdown.murderer.score}/{score_breakdown.murderer.max_score}；"
        f"关键线索 {score_breakdown.key_evidence.score}/{score_breakdown.key_evidence.max_score}；"
        f"动机 {score_breakdown.motive.score}/{score_breakdown.motive.max_score}；"
        f"手法 {score_breakdown.method.score}/{score_breakdown.method.max_score}。"
    )


def _build_evaluation(score_breakdown: Any) -> FinalVoteEvaluation:
    """
    将 ScoreBreakdown 转换成 FinalVoteEvaluation。

    为什么拆成单独方法？
    - evaluate_final_vote() 负责“读取数据 + 调用评分核心”。
    - _build_evaluation() 负责“组装返回对象”。
    - 后续如果 FinalVoteEvaluation 字段变化，只需要改这里。
    """

    score = score_breakdown.total_score
    max_score = score_breakdown.max_score

    # V0.2.0 中，完全正确意味着四项评分都拿满。
    is_correct = score == max_score

    reason = _build_reason(score_breakdown)

    return FinalVoteEvaluation(
        is_correct=is_correct,
        matched_murderer=score_breakdown.murderer.matched,
        matched_key_clue_ids=score_breakdown.key_evidence.matched_clue_ids,
        score=score,
        max_score=max_score,
        reason=reason,
        score_breakdown=score_breakdown.to_dict(),
    )


class RuleJudge:
    """
    最小规则裁判。

    当前阶段不接 LLM，只做确定性规则判断。

    V0.2.0 改造后：
    - RuleJudge 不再写死 60/40。
    - RuleJudge 从 script.rules.scoring 读取评分配置。
    - RuleJudge 从 script.truth 读取标准答案。
    - RuleJudge 调用 stery.judge.scoring.build_score_breakdown() 计算分数。

    在 Agent 工程视角中：
    - RuleJudge 是 deterministic evaluator。
    - scoring.py 是 evaluator 的核心计算模块。
    """

    def __init__(self, script: GameScript):
        self.script = script

        # 预构造 ID 集合，用于快速校验玩家提交是否合法。
        #
        # 这里保留旧设计：
        # - 玩家不能提交不存在的角色 ID。
        # - 玩家不能提交不存在的 clue_id。
        self._character_ids = {character.id for character in script.characters}
        self._clue_ids = {clue.id for clue in script.clues}

    def ensure_character_exists(self, character_id: str) -> None:
        """
        校验角色 ID 是否存在。

        这是判案前的输入合法性检查，不属于评分算法。
        """

        if character_id not in self._character_ids:
            raise ValueError(f"Unknown character_id: {character_id}")

    def ensure_clues_exist(self, clue_ids: list[str]) -> None:
        """
        校验玩家提交的关键线索 ID 是否存在。

        玩家不能提交剧本中不存在的 clue_id。
        """

        for clue_id in clue_ids:
            if clue_id not in self._clue_ids:
                raise ValueError(f"Unknown clue_id: {clue_id}")

    def evaluate_final_vote(self, vote: FinalVote) -> FinalVoteEvaluation:
        """
        评估玩家最终推理。

        数据流：
        1. 校验玩家提交的 suspect_character_id 和 key_evidence。
        2. 从 script.truth 读取标准答案。
        3. 从 script.rules.scoring 读取评分权重。
        4. 调用 build_score_breakdown() 生成可解释评分。
        5. 转换成 FinalVoteEvaluation。

        字段映射：
        - vote.suspect_character_id -> actual_murderer_id
        - vote.key_evidence         -> actual_key_evidence_ids
        - truth.key_clue_ids        -> expected_key_evidence_ids

        兼容策略：
        - 新剧本优先使用 truth.murderer_id。
        - 旧剧本没有 murderer_id 时，fallback 到 truth.id。
        """

        # 1. 判案前先做输入合法性校验。
        self.ensure_character_exists(vote.suspect_character_id)
        self.ensure_clues_exist(vote.key_evidence)

        truth = self.script.truth

        # 2. 获取标准凶手。
        #
        # V0.2.0 新字段是 truth.murderer_id。
        # 为兼容旧剧本，如果 murderer_id 缺失，则使用 truth.id。
        expected_murderer_id = truth.murderer_id or truth.id

        # 3. 当前剧本协议仍使用 key_clue_ids。
        #
        # 后续可以考虑统一命名为 key_evidence_ids，
        # 但 TASK-001 不做重命名，避免扩大影响范围。
        expected_key_clue_ids = truth.key_clue_ids

        # 4. 从 rules.scoring 读取评分配置。
        #
        # 如果旧剧本没有 scoring，则默认 40/30/15/15。
        scoring = ScoringConfig.from_rules(self.script.rules)

        # 5. 调用独立评分模块。
        #
        # RuleJudge 不再负责具体算分。
        # 这样后续如果评分规则升级，只需要改 scoring.py。
        score_breakdown = build_score_breakdown(
            scoring=scoring,
            # 玩家提交
            actual_murderer_id=vote.suspect_character_id,
            actual_key_evidence_ids=vote.key_evidence,
            actual_motive=vote.motive,
            actual_method=vote.method,
            # 标准答案
            expected_murderer_id=expected_murderer_id,
            expected_key_evidence_ids=expected_key_clue_ids,
            expected_motive=truth.motive,
            expected_method=truth.method,
            motive_keywords=truth.motive_keywords,
            method_keywords=truth.method_keywords,
        )

        # 6. 将评分拆解转换成系统原有的评估结果对象。
        return _build_evaluation(score_breakdown)

