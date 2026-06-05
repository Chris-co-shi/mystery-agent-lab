# stery/case/case_notebook_service.py

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from stery.domain import ClueVisibility
from stery.domain.models import Character, Clue, GameScript
from stery.domain.state import GameState


@dataclass(frozen=True)
class NotebookClueItem:
    """
    案件笔记本中的线索条目。

    这里不是完整 Clue 模型，而是面向玩家复盘的轻量视图。
    """

    clue_id: str
    title: str
    content: str
    visibility: str
    is_key_clue: bool
    related_character_ids: list[str] = field(default_factory=list)
    related_target_ids: list[str] = field(default_factory=list)
    reasoning_tags: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "clue_id": self.clue_id,
            "title": self.title,
            "content": self.content,
            "visibility": self.visibility,
            "is_key_clue": self.is_key_clue,
            "related_character_ids": list(self.related_character_ids),
            "related_target_ids": list(self.related_target_ids),
            "reasoning_tags": list(self.reasoning_tags),
        }


@dataclass(frozen=True)
class NotebookInvestigationItem:
    """
    案件笔记本中的调查对象记录。

    来源是 CaseRecord.metadata，而不是重新扫描 investigation_targets。
    原因：
    - Notebook 展示的是“玩家做过什么”
    - 不是“剧本里有哪些可调查对象”
    """

    target_id: str
    target_name: str
    target_type: str
    newly_discovered_clue_ids: list[str] = field(default_factory=list)
    already_discovered_clue_ids: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "target_id": self.target_id,
            "target_name": self.target_name,
            "target_type": self.target_type,
            "newly_discovered_clue_ids": list(self.newly_discovered_clue_ids),
            "already_discovered_clue_ids": list(self.already_discovered_clue_ids),
        }


@dataclass(frozen=True)
class NotebookNpcQuestionItem:
    """
    案件笔记本中的 NPC 问答摘要。
    """

    question_id: str
    target_character_id: str
    target_character_name: str
    question: str
    answer: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "question_id": self.question_id,
            "target_character_id": self.target_character_id,
            "target_character_name": self.target_character_name,
            "question": self.question,
            "answer": self.answer,
        }


@dataclass(frozen=True)
class CaseNotebook:
    """
    案件笔记本 MVP。

    注意：
    这不是自动推理结果，只是玩家已知信息的结构化整理。
    """

    discovered_clues: list[NotebookClueItem] = field(default_factory=list)
    investigated_targets: list[NotebookInvestigationItem] = field(default_factory=list)
    npc_questions: list[NotebookNpcQuestionItem] = field(default_factory=list)
    evidence_candidates: list[NotebookClueItem] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "discovered_clues": [
                item.to_dict() for item in self.discovered_clues
            ],
            "investigated_targets": [
                item.to_dict() for item in self.investigated_targets
            ],
            "npc_questions": [
                item.to_dict() for item in self.npc_questions
            ],
            "evidence_candidates": [
                item.to_dict() for item in self.evidence_candidates
            ],
        }


class CaseNotebookService:
    """
    案件笔记本服务。

    职责：
    - 从当前 GameScript + GameState 中整理玩家已知信息。
    - 给 CLI /case、后续 /submit 前预览、Session 导出提供统一数据源。

    不负责：
    - 自动判断凶手
    - 自动归因线索
    - LLM 总结
    - 解锁线索
    - 修改 GameState
    """

    def __init__(self, script: GameScript):
        self.script = script
        self._characters_by_id: dict[str, Character] = {
            character.id: character for character in script.characters
        }

    def build(self, state: GameState) -> CaseNotebook:
        """
        构建案件笔记本。

        这是当前服务的主入口。
        """

        discovered_clues = self._build_discovered_clues(state)
        investigated_targets = self._build_investigated_targets(state)
        npc_questions = self._build_npc_questions(state)

        evidence_candidates = [
            clue for clue in discovered_clues
            if clue.is_key_clue
        ]

        return CaseNotebook(
            discovered_clues=discovered_clues,
            investigated_targets=investigated_targets,
            npc_questions=npc_questions,
            evidence_candidates=evidence_candidates,
        )

    def _build_discovered_clues(self, state: GameState) -> list[NotebookClueItem]:
        """
        汇总玩家当前已知线索。

        已知线索定义：
        - PUBLIC：开局可见
        - LOCKED 且 clue.id in state.unlocked_clue_ids：已经通过调查或旧流程解锁
        - HIDDEN：不展示
        """

        items: list[NotebookClueItem] = []

        for clue in self.script.clues:
            if clue.visibility == ClueVisibility.HIDDEN:
                continue

            if not self._is_known_clue(state, clue):
                continue

            items.append(self._to_clue_item(clue))

        return items

    def _build_investigated_targets(
        self,
        state: GameState,
    ) -> list[NotebookInvestigationItem]:
        """
        从 case_records 中汇总玩家已经调查过的对象。

        这里不直接读取 script.investigation_targets。
        原因：
        - Notebook 要展示玩家做过的事情
        - 不是展示所有可做的事情
        """

        items: list[NotebookInvestigationItem] = []

        for record in getattr(state, "case_records", []):
            action_type = _enum_value(getattr(record, "action_type", ""))

            if action_type != "INVESTIGATE":
                continue

            metadata = getattr(record, "metadata", {}) or {}

            items.append(
                NotebookInvestigationItem(
                    target_id=str(metadata.get("target_id", "")),
                    target_name=str(metadata.get("target_name", "")),
                    target_type=str(metadata.get("target_type", "")),
                    newly_discovered_clue_ids=list(
                        metadata.get("newly_discovered_clue_ids", []) or []
                    ),
                    already_discovered_clue_ids=list(
                        metadata.get("already_discovered_clue_ids", []) or []
                    ),
                )
            )

        return items

    def _build_npc_questions(
        self,
        state: GameState,
    ) -> list[NotebookNpcQuestionItem]:
        """
        汇总 NPC 问答记录。

        问题和回答分别在 question_history / answer_history 中，
        通过 question_id 关联。
        """

        items: list[NotebookNpcQuestionItem] = []

        answers_by_question_id = {
            answer.question_id: answer
            for answer in getattr(state, "answer_history", [])
        }

        for question in getattr(state, "question_history", []):
            answer = answers_by_question_id.get(question.question_id)

            target_character_id = getattr(question, "target_character_id", "")
            target_character_name = self._get_character_name(target_character_id)

            items.append(
                NotebookNpcQuestionItem(
                    question_id=str(question.question_id),
                    target_character_id=target_character_id,
                    target_character_name=target_character_name,
                    question=str(getattr(question, "content", "")),
                    answer=str(getattr(answer, "content", "")) if answer else "",
                )
            )

        return items

    def _is_known_clue(self, state: GameState, clue: Clue) -> bool:
        """
        判断一条线索是否已经对玩家可见。
        """

        return (
            clue.visibility == ClueVisibility.PUBLIC
            or clue.id in state.unlocked_clue_ids
        )

    def _to_clue_item(self, clue: Clue) -> NotebookClueItem:
        """
        将 Clue 转成笔记本线索条目。
        """

        return NotebookClueItem(
            clue_id=clue.id,
            title=clue.title,
            content=clue.content,
            visibility=clue.visibility.value,
            is_key_clue=clue.is_key_clue,
            related_character_ids=list(
                getattr(clue, "related_character_ids", []) or []
            ),
            related_target_ids=list(
                getattr(clue, "related_target_ids", []) or []
            ),
            reasoning_tags=list(
                getattr(clue, "reasoning_tags", []) or []
            ),
        )

    def _get_character_name(self, character_id: str) -> str:
        """
        根据角色 ID 获取角色名。

        找不到时返回原 ID，避免 Notebook 构建失败。
        """

        character = self._characters_by_id.get(character_id)

        if character is None:
            return character_id

        return character.name


def _enum_value(value: Any) -> str:
    """
    获取 Enum 的 value。

    CaseActionType 通常是 str Enum。
    为了兼容测试中的字符串，这里做轻量处理。
    """

    return str(getattr(value, "value", value))