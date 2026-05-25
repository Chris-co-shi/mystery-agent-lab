from pydantic import BaseModel, ConfigDict, Field

from stery.application.clue_manager import ClueManager
from stery.domain.enums import ClueVisibility
from stery.domain.models import Clue, GameScript
from stery.domain.state import GameState


class ClueSearchResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    keyword: str
    unlocked_clues: list[Clue] = Field(default_factory=list)
    already_unlocked_clues: list[Clue] = Field(default_factory=list)
    message: str


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

        unlocked_clues: list[Clue] = []
        already_unlocked_clues: list[Clue] = []

        for clue in self.script.clues:
            if clue.visibility == ClueVisibility.HIDDEN:
                continue

            if not self._matches(clue, normalized_keyword):
                continue

            if clue.id in state.unlocked_clue_ids:
                already_unlocked_clues.append(clue)
                continue

            self.clue_manager.unlock_clue(state, clue.id)
            unlocked_clues.append(clue)

        if unlocked_clues:
            message = f"你发现了 {len(unlocked_clues)} 条新线索。"
        elif already_unlocked_clues:
            message = "相关线索你已经发现过了。"
        else:
            message = "没有发现新的线索。"

        state.touch()

        return ClueSearchResult(
            keyword=normalized_keyword,
            unlocked_clues=unlocked_clues,
            already_unlocked_clues=already_unlocked_clues,
            message=message,
        )

    def _matches(self, clue: Clue, keyword: str) -> bool:
        return any(keyword in item for item in clue.search_keywords)