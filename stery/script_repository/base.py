from abc import ABC, abstractmethod

from stery.domain.models import GameScript


class ScriptRepository(ABC):
    """
    游戏脚本源
    """

    @abstractmethod
    def get_script(self, script_id: str) -> GameScript:
        """
        根据 script_id 获取完整可用的剧本对象。
        """
        raise NotImplementedError

    @abstractmethod
    def list_scripts(self) -> list[str]:
        """
        列出当前仓储中可用的剧本 ID。
        """
        raise NotImplementedError