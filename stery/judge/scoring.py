# stery/judge/scoring.py

from __future__ import annotations

import math
import re
from dataclasses import asdict, dataclass
from typing import Any


@dataclass(frozen=True)
class ScoringConfig:
    """
    V0.2.0 剧本评分配置。

    这个类只表达“各部分最多多少分”，不负责具体评分逻辑。

    当前 V0.2.0 采用确定性评分：
    - murderer_score：凶手是否命中
    - key_evidence_score：关键证据命中比例
    - motive_score：动机关键词命中比例
    - method_score：手法关键词命中比例

    注意：
    1. from_rules() 只负责从 rules.scoring 中读取配置。
    2. validate() 只返回问题列表，不直接 raise。
    3. 是否阻断剧本加载，应由后续 ScriptValidator 决定。
    """

    murderer_score: int = 40
    key_evidence_score: int = 30
    motive_score: int = 15
    method_score: int = 15

    @classmethod
    def default(cls) -> "ScoringConfig":
        """
        返回 V0.2.0 默认评分配置。

        默认总分为 100：
        - 凶手 40
        - 关键证据 30
        - 动机 15
        - 手法 15
        """

        return cls()

    @classmethod
    def from_rules(cls, rules: Any) -> "ScoringConfig":
        """
        从 rules.scoring 中读取评分配置。

        这里做了兼容处理，支持：
        - dict
        - dataclass object
        - pydantic model
        - rules 为 None
        - rules.scoring 缺失

        设计取舍：
        - 读取失败时使用默认值，而不是抛异常。
        - 因为 scoring.py 是评分核心，不应该承担“剧本是否非法”的职责。
        - 后续严格校验应放到 ScriptValidator。
        """

        if rules is None:
            return cls.default()

        scoring = _read_field(rules, "scoring")
        if scoring is None:
            return cls.default()

        default = cls.default()

        return cls(
            murderer_score=_read_int_field(
                scoring,
                "murderer_score",
                default.murderer_score,
            ),
            key_evidence_score=_read_int_field(
                scoring,
                "key_evidence_score",
                default.key_evidence_score,
            ),
            motive_score=_read_int_field(
                scoring,
                "motive_score",
                default.motive_score,
            ),
            method_score=_read_int_field(
                scoring,
                "method_score",
                default.method_score,
            ),
        )

    @property
    def total_score(self) -> int:
        """
        当前评分配置的总分。
        """

        return (
            self.murderer_score
            + self.key_evidence_score
            + self.motive_score
            + self.method_score
        )

    def validate(self) -> list[str]:
        """
        轻量校验评分配置。

        返回：
            list[str]: 配置问题列表。为空表示没有发现问题。

        为什么不直接 raise？
        - scoring 模块只负责评分，不负责剧本加载失败。
        - 后续 ScriptValidator 可以调用这个方法，并决定 warning 还是 error。
        """

        errors: list[str] = []

        score_items = {
            "murderer_score": self.murderer_score,
            "key_evidence_score": self.key_evidence_score,
            "motive_score": self.motive_score,
            "method_score": self.method_score,
        }

        for field_name, value in score_items.items():
            if value <= 0:
                errors.append(
                    f"rules.scoring.{field_name} 必须大于 0，当前值为 {value}。"
                )

        if self.total_score != 100:
            errors.append(
                f"rules.scoring 总分建议为 100，当前为 {self.total_score}。"
            )

        return errors

    def to_dict(self) -> dict[str, int]:
        return asdict(self)


@dataclass(frozen=True)
class MurdererScore:
    """
    凶手评分结果。

    这是一个完全命中型评分：
    - actual_murderer_id == expected_murderer_id，则满分
    - 否则 0 分
    """

    score: int
    max_score: int
    matched: bool
    expected_murderer_id: str
    actual_murderer_id: str
    reason: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class EvidenceScore:
    """
    关键证据评分结果。

    关键证据按命中比例评分：
    - 命中 2 / 3 条，得到 2/3 的 key_evidence_score
    - 玩家重复提交同一证据不重复加分
    """

    score: int
    max_score: int
    matched_clue_ids: list[str]
    missing_clue_ids: list[str]
    reason: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class KeywordScore:
    """
    动机 / 手法关键词评分结果。

    V0.2.0 暂时采用简单 contains 匹配：
    - 玩家文本包含关键词，则认为该关键词命中。
    - 暂不做 keyword_groups。
    - 暂不做 LLM 语义评分。
    """

    score: int
    max_score: int
    matched_keywords: list[str]
    missing_keywords: list[str]
    reason: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ScoreBreakdown:
    """
    最终评分拆解。

    这个对象是 V0.2.0 的关键产物：
    它不只告诉玩家“得了多少分”，还说明每一部分为什么得分或扣分。

    后续用途：
    - /submit 展示评分
    - /review 回放最终提交
    - JSON / Markdown 导出
    - 未来 LLMJudge / HostJudge 对照使用
    """

    murderer: MurdererScore
    key_evidence: EvidenceScore
    motive: KeywordScore
    method: KeywordScore

    @property
    def total_score(self) -> int:
        """
        实际得分。
        """

        return (
            self.murderer.score
            + self.key_evidence.score
            + self.motive.score
            + self.method.score
        )

    @property
    def max_score(self) -> int:
        """
        满分。

        正常情况下应该是 100，但这里不硬编码。
        因为后续允许剧本自定义评分总分。
        """

        return (
            self.murderer.max_score
            + self.key_evidence.max_score
            + self.motive.max_score
            + self.method.max_score
        )

    def to_dict(self) -> dict[str, Any]:
        """
        转为 dict，便于：
        - FinalVoteEvaluation 持久化
        - JSON 导出
        - Markdown 渲染
        - 测试断言
        """

        return {
            "murderer": self.murderer.to_dict(),
            "key_evidence": self.key_evidence.to_dict(),
            "motive": self.motive.to_dict(),
            "method": self.method.to_dict(),
            "total_score": self.total_score,
            "max_score": self.max_score,
        }


def score_murderer(
    *,
    actual_murderer_id: str,
    expected_murderer_id: str,
    max_score: int,
) -> MurdererScore:
    """
    计算凶手得分。

    参数：
        actual_murderer_id:
            玩家提交的凶手 ID。

        expected_murderer_id:
            剧本 truth 中配置的正确凶手 ID。

        max_score:
            凶手判断满分。

    返回：
        MurdererScore
    """

    matched = actual_murderer_id == expected_murderer_id

    return MurdererScore(
        score=max_score if matched else 0,
        max_score=max_score,
        matched=matched,
        expected_murderer_id=expected_murderer_id,
        actual_murderer_id=actual_murderer_id,
        reason=(
            f"命中正确凶手：{expected_murderer_id}。"
            if matched
            else f"凶手不匹配，提交：{actual_murderer_id}，正确：{expected_murderer_id}。"
        ),
    )


def score_key_evidence(
    *,
    actual_clue_ids: list[str],
    expected_clue_ids: list[str],
    max_score: int,
) -> EvidenceScore:
    """
    计算关键证据得分。

    评分规则：
    - 以 expected_clue_ids 为标准答案集合。
    - 玩家提交的 actual_clue_ids 命中多少，就按比例给分。
    - 玩家重复提交同一 clue_id，不重复加分。
    - matched_clue_ids / missing_clue_ids 按 expected_clue_ids 顺序返回。

    为什么按 expected_clue_ids 顺序？
    - 剧本作者在 truth.key_evidence_ids 中的顺序通常更符合推理展示顺序。
    - sorted() 虽然稳定，但会破坏作者定义的语义顺序。
    """

    actual_unique = _unique_preserve_order(actual_clue_ids or [])
    expected_unique = _unique_preserve_order(expected_clue_ids or [])

    if not expected_unique:
        return EvidenceScore(
            score=0,
            max_score=max_score,
            matched_clue_ids=[],
            missing_clue_ids=[],
            reason="剧本未配置关键证据，关键证据不得分。",
        )

    actual_set = set(actual_unique)

    matched_clue_ids = [
        clue_id for clue_id in expected_unique if clue_id in actual_set
    ]
    missing_clue_ids = [
        clue_id for clue_id in expected_unique if clue_id not in actual_set
    ]

    raw_score = len(matched_clue_ids) / len(expected_unique) * max_score
    score = _round_half_up(raw_score)

    return EvidenceScore(
        score=score,
        max_score=max_score,
        matched_clue_ids=matched_clue_ids,
        missing_clue_ids=missing_clue_ids,
        reason=(
            f"关键证据命中 {len(matched_clue_ids)}/{len(expected_unique)} 条："
            f"命中「{_join_or_none(matched_clue_ids)}」，"
            f"缺失「{_join_or_none(missing_clue_ids)}」。"
        ),
    )


def score_keywords(
    *,
    actual_text: str,
    expected_keywords: list[str],
    max_score: int,
    label: str,
    fallback_expected_text: str | None = None,
) -> KeywordScore:
    """
    计算动机 / 手法关键词得分。

    V0.2.0 规则：
    - expected_keywords 是标准关键词数组。
    - 玩家答案中包含一个关键词，则该关键词命中。
    - 命中比例 = 命中关键词数量 / 标准关键词数量。
    - 最终得分 = 命中比例 * max_score。

    示例：
        expected_keywords = ["镇静剂", "红酒", "投药"]
        actual_text = "凶手把镇静剂混入红酒"

        命中 2/3，若 max_score = 15，则得 10 分。

    为什么不用 LLM 判断？
    - V0.2.0 要保持确定性。
    - 先解决 RuleJudge 写死评分和手法不参与评分的问题。
    - LLMJudge 留到后续版本。
    """

    normalized_actual = _normalize_text(actual_text)

    # 去掉空关键词，并保留剧本配置顺序。
    keywords = _unique_preserve_order(
        [keyword for keyword in (expected_keywords or []) if keyword and keyword.strip()]
    )

    if not keywords:
        return _score_with_fallback_text(
            normalized_actual=normalized_actual,
            fallback_expected_text=fallback_expected_text,
            max_score=max_score,
            label=label,
        )

    matched_keywords: list[str] = []
    missing_keywords: list[str] = []

    for keyword in keywords:
        normalized_keyword = _normalize_text(keyword)

        if normalized_keyword and normalized_keyword in normalized_actual:
            matched_keywords.append(keyword)
        else:
            missing_keywords.append(keyword)

    raw_score = len(matched_keywords) / len(keywords) * max_score
    score = _round_half_up(raw_score)

    return KeywordScore(
        score=score,
        max_score=max_score,
        matched_keywords=matched_keywords,
        missing_keywords=missing_keywords,
        reason=(
            f"{label}命中 {len(matched_keywords)}/{len(keywords)}："
            f"命中「{_join_or_none(matched_keywords)}」，"
            f"缺失「{_join_or_none(missing_keywords)}」。"
        ),
    )


def build_score_breakdown(
    *,
    scoring: ScoringConfig,
    actual_murderer_id: str,
    expected_murderer_id: str,
    actual_key_evidence_ids: list[str],
    expected_key_evidence_ids: list[str],
    actual_motive: str,
    motive_keywords: list[str],
    actual_method: str,
    method_keywords: list[str],
    expected_motive: str = "",
    expected_method: str = "",
) -> ScoreBreakdown:
    """
    构建完整评分拆解。

    这是 RuleJudge 后续最应该调用的入口。

    输入来自：
    - scoring: script.rules.scoring
    - expected_*: script.truth
    - actual_*: 玩家 FinalVote

    输出：
    - ScoreBreakdown
    """

    murderer_score = score_murderer(
        actual_murderer_id=actual_murderer_id,
        expected_murderer_id=expected_murderer_id,
        max_score=scoring.murderer_score,
    )

    evidence_score = score_key_evidence(
        actual_clue_ids=actual_key_evidence_ids,
        expected_clue_ids=expected_key_evidence_ids,
        max_score=scoring.key_evidence_score,
    )

    motive_score = score_keywords(
        actual_text=actual_motive,
        expected_keywords=motive_keywords,
        fallback_expected_text=expected_motive,
        max_score=scoring.motive_score,
        label="动机关键词",
    )

    method_score = score_keywords(
        actual_text=actual_method,
        expected_keywords=method_keywords,
        fallback_expected_text=expected_method,
        max_score=scoring.method_score,
        label="手法关键词",
    )

    return ScoreBreakdown(
        murderer=murderer_score,
        key_evidence=evidence_score,
        motive=motive_score,
        method=method_score,
    )


def _score_with_fallback_text(
    *,
    normalized_actual: str,
    fallback_expected_text: str | None,
    max_score: int,
    label: str,
) -> KeywordScore:
    """
    旧剧本兼容逻辑。

    背景：
    V0.1.x 剧本可能只有 truth.motive / truth.method，
    没有 motive_keywords / method_keywords。

    兼容规则：
    - 如果没有关键词，但有 fallback_expected_text，
      则只有玩家文本完整包含 fallback 文本时才给满分。
    - 这不是理想评分方式，但可以保证旧剧本不崩。
    """

    fallback_text = fallback_expected_text or ""
    normalized_fallback = _normalize_text(fallback_text)

    if normalized_fallback:
        matched = normalized_fallback in normalized_actual

        return KeywordScore(
            score=max_score if matched else 0,
            max_score=max_score,
            matched_keywords=[fallback_text] if matched else [],
            missing_keywords=[] if matched else [fallback_text],
            reason=(
                f"剧本未配置 {label}，使用完整文本兼容匹配，已命中。"
                if matched
                else f"剧本未配置 {label}，完整文本未命中。"
            ),
        )

    return KeywordScore(
        score=0,
        max_score=max_score,
        matched_keywords=[],
        missing_keywords=[],
        reason=f"剧本未配置 {label}，该项不得分。",
    )


def _round_half_up(value: float) -> int:
    """
    常规四舍五入。

    Python 内置 round() 使用银行家舍入：
        round(2.5) == 2

    对评分系统来说，这不符合直觉。
    所以这里使用：
        floor(value + 0.5)
    """

    return math.floor(value + 0.5)


def _normalize_text(text: str | None) -> str:
    """
    文本归一化，用于关键词 contains 匹配。

    当前只做轻量处理：
    - None -> ""
    - 转小写
    - 移除所有空白字符

    不做：
    - 同义词替换
    - 繁简转换
    - 语义理解
    - LLM 判断

    这些都留给后续版本。
    """

    if text is None:
        return ""

    return re.sub(r"\s+", "", str(text).strip().lower())


def _join_or_none(values: list[str]) -> str:
    """
    用于生成 reason 文本。

    空列表展示为“无”，避免输出空字符串。
    """

    if not values:
        return "无"

    return "、".join(values)


def _unique_preserve_order(values: list[str]) -> list[str]:
    """
    去重并保留原始顺序。

    为什么不用 set？
    - set 会丢失顺序。
    - 评分展示时，顺序会影响玩家理解。
    """

    seen: set[str] = set()
    result: list[str] = []

    for value in values:
        if value in seen:
            continue

        seen.add(value)
        result.append(value)

    return result


def _read_field(obj: Any, field_name: str, default: Any = None) -> Any:
    """
    兼容读取 dict / object 字段。

    这个函数暂时放在 scoring.py 内部。
    后续如果多个模块都需要，再考虑抽到公共工具。
    """

    if obj is None:
        return default

    if isinstance(obj, dict):
        return obj.get(field_name, default)

    return getattr(obj, field_name, default)


def _read_int_field(obj: Any, field_name: str, default: int) -> int:
    """
    读取整数字段。

    如果字段缺失或无法转换为 int，则返回默认值。

    注意：
    这里不抛异常，是为了兼容旧剧本。
    严格校验留给 ScriptValidator。
    """

    value = _read_field(obj, field_name, default)

    try:
        return int(value)
    except (TypeError, ValueError):
        return default