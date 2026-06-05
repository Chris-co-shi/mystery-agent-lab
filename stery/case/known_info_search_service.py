# stery/clue/known_info_search_service.py

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

from stery.domain import GameState, ClueVisibility
from stery.domain.models import Clue, GameScript


@dataclass(frozen=True)
class KnownInfoSearchMatch:
    """
    已知信息搜索命中项。

    这个对象不是剧本协议模型，而是搜索结果 DTO。

    source_type:
        CLUE         已知线索
        CASE_RECORD  案件记录
        QA           问答记录

    title:
        搜索结果标题，给 CLI 展示使用。

    content:
        搜索结果正文，给 CLI 展示使用。

    source_id:
        来源 ID，例如 clue_id、record_id、question_id。
    """

    source_type: str
    title: str
    content: str
    source_id: str
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "source_type": self.source_type,
            "title": self.title,
            "content": self.content,
            "source_id": self.source_id,
            "metadata": dict(self.metadata),
        }


@dataclass(frozen=True)
class KnownInfoSearchResult:
    """
    已知信息检索结果。

    注意：
    这里没有 newly_unlocked_clues。
    因为 /search 在 V0.2.0 中不再负责解锁线索。
    """

    keyword: str
    matches: list[KnownInfoSearchMatch] = field(default_factory=list)
    message: str = ""

    @property
    def has_matches(self) -> bool:
        return len(self.matches) > 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "keyword": self.keyword,
            "matches": [match.to_dict() for match in self.matches],
            "message": self.message,
        }


def _search_case_records(
        *,
        state: GameState,
        normalized_keyword: str,
) -> list[KnownInfoSearchMatch]:
    """
    搜索案件记录。

    例如：
    - 玩家调查了：尸体；发现 1 条新线索。
    - 玩家询问了：祁曼殊
    - 玩家搜索了：药剂柜

    这里只读取 record.title / record.summary。
    metadata 可以作为补充匹配内容，但不直接展示。
    """

    matches: list[KnownInfoSearchMatch] = []

    for record in getattr(state, "case_records", []):
        title = str(getattr(record, "title", ""))
        summary = str(getattr(record, "summary", ""))
        metadata = getattr(record, "metadata", {}) or {}

        searchable_text = " ".join(
            [
                title,
                summary,
                str(metadata),
            ]
        )

        if normalized_keyword not in _normalize_text(searchable_text):
            continue

        record_id = str(
            getattr(record, "record_id", "")
            or getattr(record, "id", "")
            or len(matches) + 1
        )

        matches.append(
            KnownInfoSearchMatch(
                source_type="CASE_RECORD",
                title=title or "案件记录",
                content=summary,
                source_id=record_id,
                metadata=dict(metadata) if isinstance(metadata, dict) else {},
            )
        )

    return matches


def _search_question_answers(
        *,
        state: GameState,
        normalized_keyword: str,
) -> list[KnownInfoSearchMatch]:
    """
    搜索问答记录。

    这里把同一个 question_id 的问题和回答组合成一个 QA 搜索结果。
    """

    matches: list[KnownInfoSearchMatch] = []

    answers_by_question_id = {
        answer.question_id: answer
        for answer in getattr(state, "answer_history", [])
    }

    for question in getattr(state, "question_history", []):
        answer = answers_by_question_id.get(question.question_id)

        question_content = str(getattr(question, "content", ""))
        answer_content = (
            str(getattr(answer, "content", ""))
            if answer is not None
            else ""
        )

        searchable_text = f"{question_content} {answer_content}"

        if normalized_keyword not in _normalize_text(searchable_text):
            continue

        content = (
            f"玩家：{question_content}\n"
            f"NPC：{answer_content or '<暂无回答记录>'}"
        )

        matches.append(
            KnownInfoSearchMatch(
                source_type="QA",
                title="问答记录",
                content=content,
                source_id=str(question.question_id),
                metadata={
                    "question_id": question.question_id,
                    "target_character_id": getattr(
                        question,
                        "target_character_id",
                        "",
                    ),
                },
            )
        )

    return matches


def _is_known_clue(state: GameState, clue: Clue) -> bool:
    """
    判断一条线索是否已经对玩家可见。
    """

    return _is_public_clue(clue) or clue.id in state.unlocked_clue_ids


class KnownInfoSearchService:
    """
    已知信息检索服务。

    职责：
    - 只检索玩家已经知道的信息。
    - 不解锁新的 LOCKED 线索。
    - 不返回 HIDDEN 线索。
    - 不修改 GameState。

    这和旧 ClueSearchService 的区别很重要：
    - ClueSearchService：关键词搜索并解锁线索。
    - KnownInfoSearchService：在已知信息中检索，不解锁。
    """

    def __init__(self, script: GameScript):
        self.script = script
        self._clues_by_id: dict[str, Clue] = {
            clue.id: clue for clue in script.clues
        }

    def search(self, *, state: GameState, keyword: str) -> KnownInfoSearchResult:
        """
        在已知信息中搜索。

        参数：
            state:
                当前游戏状态。这里只读取，不修改。

            keyword:
                玩家输入的搜索关键词。

        返回：
            KnownInfoSearchResult

        搜索范围：
            1. PUBLIC 线索
            2. state.unlocked_clue_ids 中的线索
            3. state.case_records
            4. state.question_history / state.answer_history
        """

        normalized_keyword = _normalize_text(keyword)

        if not normalized_keyword:
            return KnownInfoSearchResult(
                keyword=keyword,
                matches=[],
                message="搜索关键词不能为空。",
            )

        matches: list[KnownInfoSearchMatch] = []

        matches.extend(
            self._search_known_clues(
                state=state,
                normalized_keyword=normalized_keyword,
            )
        )

        matches.extend(
            _search_case_records(
                state=state,
                normalized_keyword=normalized_keyword,
            )
        )

        matches.extend(
            _search_question_answers(
                state=state,
                normalized_keyword=normalized_keyword,
            )
        )

        message = (
            f"在已知信息中找到 {len(matches)} 条匹配结果。"
            if matches
            else "没有在已知信息中找到匹配结果。可以尝试先调查相关地点、尸体或物品。"
        )

        return KnownInfoSearchResult(
            keyword=keyword,
            matches=matches,
            message=message,
        )

    def _search_known_clues(
            self,
            *,
            state: GameState,
            normalized_keyword: str,
    ) -> list[KnownInfoSearchMatch]:
        """
        搜索已知线索。

        已知线索定义：
        - PUBLIC 线索：开局可见
        - 已解锁线索：clue.id in state.unlocked_clue_ids

        LOCKED 但未解锁的线索不会参与搜索。
        HIDDEN 线索不会参与搜索。
        """

        matches: list[KnownInfoSearchMatch] = []

        for clue in self.script.clues:
            if _is_hidden_clue(clue):
                continue

            if not _is_known_clue(state, clue):
                continue

            if not _matches_clue(clue, normalized_keyword):
                continue

            matches.append(
                KnownInfoSearchMatch(
                    source_type="CLUE",
                    title=clue.title,
                    content=clue.content,
                    source_id=clue.id,
                    metadata={
                        "clue_id": clue.id,
                        "visibility": _clue_visibility_value(clue),
                    },
                )
            )

        return matches


def _matches_clue(clue: Clue, normalized_keyword: str) -> bool:
    """
    判断 keyword 是否命中线索。

    匹配范围：
    - clue.id
    - clue.title
    - clue.content
    - clue.search_keywords
    - clue.related_character_ids
    - clue.reasoning_tags
    """

    searchable_parts = [
        clue.id,
        clue.title,
        clue.content,
        " ".join(getattr(clue, "search_keywords", []) or []),
        " ".join(getattr(clue, "related_character_ids", []) or []),
        " ".join(getattr(clue, "reasoning_tags", []) or []),
    ]

    searchable_text = " ".join(searchable_parts)

    return normalized_keyword in _normalize_text(searchable_text)


def _normalize_text(text: str | None) -> str:
    """
    轻量文本归一化。

    当前只做：
    - None -> ""
    - 转小写
    - 移除空白字符

    不做：
    - 分词
    - 同义词
    - 向量检索
    - LLM 总结
    """

    if text is None:
        return ""

    return re.sub(r"\s+", "", str(text).strip().lower())


def _clue_visibility_value(clue: Clue) -> str:
    """
    返回线索 visibility 的原始值，用于 metadata / 测试 / 展示。

    不直接使用 str(clue.visibility)，原因：
    - IDE 会提示 ClueVisibility 没有定义 __str__ / __repr__。
    - Enum 的 str() 结果可能是 "ClueVisibility.PUBLIC"，不是 "PUBLIC"。
    - 这里我们真正需要的是 enum.value。
    """

    return clue.visibility.value


def _is_public_clue(clue: Clue) -> bool:
    """
    判断是否为 PUBLIC 线索。

    使用枚举直接比较，而不是转字符串比较。
    这样类型更安全，也避免 IDE 静态检查警告。
    """

    return clue.visibility == ClueVisibility.PUBLIC


def _is_hidden_clue(clue: Clue) -> bool:
    """
    判断是否为 HIDDEN 线索。

    如果你的 ClueVisibility 已经有 HIDDEN，直接枚举比较即可。
    """

    return clue.visibility == ClueVisibility.HIDDEN
