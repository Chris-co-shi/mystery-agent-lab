from pydantic import BaseModel

from stery.application.clue_manager import ClueManager
from stery.domain.enums import ClueVisibility
from stery.domain.models import Clue, GameScript
from stery.domain.state import GameState


class ClueSearchResult(BaseModel):
    # 玩家本次搜索关键词
    keyword: str
    # 本次关键词命中的所有线索
    matched_clues: list[Clue]
    # 本次搜索新解锁的线索
    newly_unlocked_clues: list[Clue]
    # 之前已经解锁、本次又被命中的线索
    already_unlocked_clues: list[Clue]
    # 给 CLI 展示的摘要消息
    message: str

    @property
    def unlocked_clues(self) -> list[Clue]:
        """
        临时兼容旧代码。
        后续 CLI 全部迁移到 newly_unlocked_clues 后可以删除。
        """
        return self.newly_unlocked_clues


class ClueSearchService:
    """
    线索搜证服务。

    职责：
    - 根据玩家输入关键词匹配可发现线索
    - 解锁 LOCKED 线索
    - 不展示 HIDDEN 线索
    - 不直接搜索 clue.content，避免泄露线索正文
    """


    def __init__(self, script: GameScript):
        self.script = script
        self.clue_manager = ClueManager(script)


    def search(self, state: GameState, keyword: str) -> ClueSearchResult:
        normalized_keyword = keyword.strip()
        if not normalized_keyword:
            raise ValueError("Search keyword cannot be empty.")

        matched_clues: list[Clue] = []
        newly_unlocked_clues: list[Clue] = []
        already_unlocked_clues: list[Clue] = []

        for clue in self.script.clues:
            if clue.visibility == ClueVisibility.HIDDEN:
                continue

            if not self._matches(clue, normalized_keyword):
                continue

            matched_clues.append(clue)

            if clue.id in state.unlocked_clue_ids:
                already_unlocked_clues.append(clue)
                continue

            self.clue_manager.unlock_clue(state, clue.id)
            newly_unlocked_clues.append(clue)

        message = self._build_message(
            matched_count=len(matched_clues),
            newly_unlocked_count=len(newly_unlocked_clues),
            already_unlocked_count=len(already_unlocked_clues),
        )
        if matched_clues:
            state.touch()

        return ClueSearchResult(
            keyword=normalized_keyword,
            matched_clues=matched_clues,
            newly_unlocked_clues=newly_unlocked_clues,
            already_unlocked_clues=already_unlocked_clues,
            message=message,
        )


    def _matches(self, clue: Clue, keyword: str) -> bool:
        normalized_keyword = keyword.lower()

        searchable_items = [
            clue.id,
            clue.title,
            *clue.search_keywords,
        ]

        return any(
            normalized_keyword in item.lower()
            for item in searchable_items
        )


    def _build_message(
            self,
            matched_count: int,
            newly_unlocked_count: int,
            already_unlocked_count: int,
    ) -> str:
        if matched_count == 0:
            return "没有发现相关线索。可以尝试搜索地点、物品、人物或时间。"

        return (
            f"本次搜索命中 {matched_count} 条线索，"
            f"新发现 {newly_unlocked_count} 条，"
            f"已发现过 {already_unlocked_count} 条。"
        )
