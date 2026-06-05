# stery/judge/scoring.py

from __future__ import annotations

import re
from dataclasses import asdict, dataclass, field
from decimal import Decimal, ROUND_HALF_UP
from typing import Any


@dataclass(frozen=True)
class ScoringConfig:
    """
    V0.2.0 剧本评分配置。

    这个类只表达“每个评分项最多多少分”，不负责具体评分逻辑。

    当前 V0.2.0 采用确定性评分：
    - murderer_score：凶手是否命中。
    - key_evidence_score：关键证据命中比例。
    - motive_score：动机关键词命中比例。
    - method_score：手法关键词命中比例。

    注意：
    - from_rules() 负责兼容读取 rules.scoring。
    - validate() 只返回问题列表，不直接 raise。
    - 剧本是否非法，应由 ScriptValidator 决定，而不是评分模块决定。
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

        兼容输入：
        - dict
        - dataclass object
        - pydantic model
        - rules 为 None
        - rules.scoring 缺失

        读取失败时使用默认值，避免旧剧本直接崩溃。
        严格校验应交给 ScriptValidator。
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
        """当前评分配置的总分。"""

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

    内部仍使用 character_id 做确定性匹配。
    玩家展示层如果需要显示角色名称，应在 CLI / exporter 中转换。
    """

    score: int
    max_score: int
    matched: bool
    expected_murderer_id: str
    actual_murderer_id: str
    reason: str

    def to_dict(self) -> dict[str, Any]:
        """
        转成 dict。

        除了保留旧字段，也额外提供 submitted_ids / expected_ids / matched_ids / missing_ids，
        方便前端或 CLI 使用统一结构展示评分项。
        """

        matched_ids = [self.expected_murderer_id] if self.matched and self.expected_murderer_id else []
        missing_ids = [] if self.matched else ([self.expected_murderer_id] if self.expected_murderer_id else [])

        return {
            "score": self.score,
            "max_score": self.max_score,
            "matched": self.matched,
            "expected_murderer_id": self.expected_murderer_id,
            "actual_murderer_id": self.actual_murderer_id,
            "reason": self.reason,
            "submitted_ids": [self.actual_murderer_id] if self.actual_murderer_id else [],
            "expected_ids": [self.expected_murderer_id] if self.expected_murderer_id else [],
            "matched_ids": matched_ids,
            "missing_ids": missing_ids,
        }


@dataclass(frozen=True)
class EvidenceScore:
    """
    关键证据评分结果。

    关键证据按命中比例评分：
    - 玩家提交 clue_id。
    - 剧本标准答案也是 clue_id。
    - 评分模块只负责 ID 匹配。
    - clue_id -> 线索标题 的玩家可读化交给 CLI / Markdown exporter。

    这就是方案 B 的核心：
    - 内部继续用 ID，保证稳定、可测试。
    - score_breakdown 中保留 matched_ids / missing_ids 等结构化字段。
    - reason 不再拼接一长串 clue_id。
    """

    score: int
    max_score: int
    submitted_clue_ids: list[str] = field(default_factory=list)
    expected_clue_ids: list[str] = field(default_factory=list)
    matched_clue_ids: list[str] = field(default_factory=list)
    missing_clue_ids: list[str] = field(default_factory=list)
    reason: str = ""

    def to_dict(self) -> dict[str, Any]:
        """
        转成 dict。

        兼容旧字段：
        - matched_clue_ids
        - missing_clue_ids

        新增统一结构化字段：
        - submitted_ids
        - expected_ids
        - matched_ids
        - missing_ids

        CLI 优先读取 matched_ids / missing_ids 并转成线索标题。
        """

        return {
            "score": self.score,
            "max_score": self.max_score,
            "reason": self.reason,
            "submitted_clue_ids": list(self.submitted_clue_ids),
            "expected_clue_ids": list(self.expected_clue_ids),
            "matched_clue_ids": list(self.matched_clue_ids),
            "missing_clue_ids": list(self.missing_clue_ids),
            "submitted_ids": list(self.submitted_clue_ids),
            "expected_ids": list(self.expected_clue_ids),
            "matched_ids": list(self.matched_clue_ids),
            "missing_ids": list(self.missing_clue_ids),
        }


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
    expected_keywords: list[str] = field(default_factory=list)
    matched_keywords: list[str] = field(default_factory=list)
    missing_keywords: list[str] = field(default_factory=list)
    reason: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "score": self.score,
            "max_score": self.max_score,
            "reason": self.reason,
            "expected_keywords": list(self.expected_keywords),
            "matched_keywords": list(self.matched_keywords),
            "missing_keywords": list(self.missing_keywords),
        }


@dataclass(frozen=True)
class ScoreBreakdown:
    """
    最终评分拆解。

    这个对象是 RuleJudge 的结构化评分结果：
    - murderer：凶手评分。
    - key_evidence：关键证据评分。
    - motive：动机关键词评分。
    - method：手法关键词评分。
    """

    murderer: MurdererScore
    key_evidence: EvidenceScore
    motive: KeywordScore
    method: KeywordScore

    @property
    def total_score(self) -> int:
        """实际得分。"""

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

        正常情况下应该是 100，但这里不硬编码，允许剧本自定义评分总分。
        """

        return (
            self.murderer.max_score
            + self.key_evidence.max_score
            + self.motive.max_score
            + self.method.max_score
        )

    def to_dict(self) -> dict[str, Any]:
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
        actual_murderer_id: str | None,
        expected_murderer_id: str | None,
        max_score: int,
) -> MurdererScore:
    """
    凶手评分。

    凶手仍然使用 character_id 做确定性匹配。
    玩家界面是否显示角色名称，由 CLI 决定。
    """

    actual_id = (actual_murderer_id or "").strip()
    expected_id = (expected_murderer_id or "").strip()

    matched = bool(actual_id and expected_id and actual_id == expected_id)

    return MurdererScore(
        score=max_score if matched else 0,
        max_score=max_score,
        matched=matched,
        expected_murderer_id=expected_id,
        actual_murderer_id=actual_id,
        reason="命中正确凶手。" if matched else "未命中正确凶手。",
    )


def score_key_evidence(
        *,
        actual_clue_ids: list[str] | tuple[str, ...] | None,
        expected_clue_ids: list[str] | tuple[str, ...] | None,
        max_score: int,
) -> EvidenceScore:
    """
    关键证据评分。

    内部规则：
    - actual_clue_ids：玩家提交的关键证据 clue_id。
    - expected_clue_ids：truth.key_clue_ids / truth.key_evidence_ids。
    - 分数按命中比例计算。
    - 结果保留 matched_clue_ids / missing_clue_ids 和 matched_ids / missing_ids。

    重要：
    - reason 只描述数量，不拼接 clue_id。
    - clue_id 只放在结构化字段中。
    """

    submitted_ids = _unique_preserve_order(actual_clue_ids)
    expected_ids = _unique_preserve_order(expected_clue_ids)

    if max_score <= 0:
        return EvidenceScore(
            score=0,
            max_score=max_score,
            submitted_clue_ids=submitted_ids,
            expected_clue_ids=expected_ids,
            matched_clue_ids=[],
            missing_clue_ids=expected_ids,
            reason="关键证据评分项未启用。",
        )

    if not expected_ids:
        return EvidenceScore(
            score=max_score,
            max_score=max_score,
            submitted_clue_ids=submitted_ids,
            expected_clue_ids=[],
            matched_clue_ids=[],
            missing_clue_ids=[],
            reason="剧本未配置关键证据，默认给满分。",
        )

    submitted_set = set(submitted_ids)

    matched_ids = [
        clue_id
        for clue_id in expected_ids
        if clue_id in submitted_set
    ]

    missing_ids = [
        clue_id
        for clue_id in expected_ids
        if clue_id not in submitted_set
    ]

    score = _round_half_up(
        max_score * len(matched_ids) / len(expected_ids)
    )

    return EvidenceScore(
        score=score,
        max_score=max_score,
        submitted_clue_ids=submitted_ids,
        expected_clue_ids=expected_ids,
        matched_clue_ids=matched_ids,
        missing_clue_ids=missing_ids,
        reason=f"关键证据命中 {len(matched_ids)}/{len(expected_ids)} 条。",
    )


def score_keywords(
        *,
        actual_text: str,
        expected_keywords: list[str] | tuple[str, ...] | None,
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

    注意：
    - 关键词本身是玩家可读文本，因此可以展示。
    - reason 只描述数量，命中/缺失明细放结构化字段中。
    """

    normalized_actual = _normalize_text(actual_text)

    keywords = _unique_preserve_order(
        [keyword for keyword in (expected_keywords or []) if keyword and keyword.strip()]
    )

    if max_score <= 0:
        return KeywordScore(
            score=0,
            max_score=max_score,
            expected_keywords=keywords,
            matched_keywords=[],
            missing_keywords=keywords,
            reason=f"{label}评分项未启用。",
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

    score = _round_half_up(
        max_score * len(matched_keywords) / len(keywords)
    )

    return KeywordScore(
        score=score,
        max_score=max_score,
        expected_keywords=keywords,
        matched_keywords=matched_keywords,
        missing_keywords=missing_keywords,
        reason=f"{label}命中 {len(matched_keywords)}/{len(keywords)}。",
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

    输入来自：
    - scoring: script.rules.scoring
    - expected_*: script.truth
    - actual_*: 玩家 FinalVote

    输出：
    - ScoreBreakdown

    这里不做任何玩家可读化转换，例如 clue_id -> clue.title。
    这些转换属于 CLI / exporter 的职责。
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
            expected_keywords=[fallback_text],
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
        expected_keywords=[],
        matched_keywords=[],
        missing_keywords=[],
        reason=f"剧本未配置 {label}，该项不得分。",
    )


def _round_half_up(value: float) -> int:
    """
    四舍五入，避免 Python round 的 bankers rounding 行为。

    例如：
    - round(2.5) 在 Python 中可能得到 2。
    - 这里固定得到 3。
    """

    return int(
        Decimal(str(value)).quantize(
            Decimal("1"),
            rounding=ROUND_HALF_UP,
        )
    )


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
    """

    if text is None:
        return ""

    return re.sub(r"\s+", "", str(text).strip().lower())


def _unique_preserve_order(items: list[str] | tuple[str, ...] | None) -> list[str]:
    """
    去重但保留顺序。

    用途：
    - 玩家可能重复提交同一个 clue_id。
    - 剧本 truth.key_evidence_ids 也可能误配置重复。
    - 评分时应避免重复项影响分数。
    """

    if not items:
        return []

    result: list[str] = []
    seen: set[str] = set()

    for item in items:
        value = str(item).strip()

        if not value:
            continue

        if value in seen:
            continue

        seen.add(value)
        result.append(value)

    return result


def _read_field(obj: Any, field_name: str, default: Any = None) -> Any:
    """
    兼容读取 dict / object 字段。
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
    """

    value = _read_field(obj, field_name, default)

    try:
        return int(value)
    except (TypeError, ValueError):
        return default
