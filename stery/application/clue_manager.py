from stery.domain.enums import ClueVisibility
from stery.domain.models import Clue, GameScript
from stery.domain.state import GameState


class ClueManager:
    """
    线索管理器。

    负责：
    - 初始化默认可见线索
    - 查询当前可见线索
    - 解锁线索
    - 防止 HIDDEN 线索被普通流程解锁
    """

    def __init__(self, script: GameScript):
        self.script = script

    def get_initial_unlocked_clue_ids(self) -> set[str]:
        return {
            clue.id
            for clue in self.script.clues
            if clue.visibility == ClueVisibility.PUBLIC
        }

    def list_available_clues(self, state: GameState) -> list[Clue]:
        available: list[Clue] = []

        for clue in self.script.clues:
            if clue.visibility == ClueVisibility.HIDDEN:
                continue

            if clue.id in state.unlocked_clue_ids:
                available.append(clue)

        return available

    def unlock_clue(self, state: GameState, clue_id: str) -> GameState:
        clue = self._find_clue(clue_id)

        if clue.visibility == ClueVisibility.HIDDEN:
            raise ValueError(f"Hidden clue cannot be unlocked directly: {clue_id}")

        state.unlocked_clue_ids.add(clue_id)
        state.touch()
        return state

    def _find_clue(self, clue_id: str) -> Clue:
        for clue in self.script.clues:
            if clue.id == clue_id:
                return clue

        raise ValueError(f"Unknown clue_id: {clue_id}")
