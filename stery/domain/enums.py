from enum import Enum, auto

"""
定义枚举
"""


class GamePhase(Enum):
    """

    """
    START = "START"
    # 背景_简介
    BACKGROUND_INTRO = "BACKGROUND_INTRO"
    # 自由提问
    FREE_QUESTION = "FREE_QUESTION"
    # 搜索线索
    SEARCH_CLUE = "SEARCH_CLUE"
    # 最终投票
    FINAL_VOTE = "FINAL_VOTE"
    # 揭示真相
    REVEAL_TRUTH = "REVEAL_TRUTH"
    END = "END"


class ClueVisibility(Enum):
    """线索可见性"""
    # 公开
    PUBLIC = "PUBLIC"
    #  锁定
    LOCKED = "LOCKED"
    # 隐藏
    HIDDEN = "HIDDEN"


class InvestigationRoundStatus(Enum):
    """调查轮次状态"""
    OPEN = "OPEN"
    CLOSED = "CLOSED"


class CaseActionType(Enum):
    """案件操作类型"""
    SEARCH = "SEARCH"
    DISCOVER_CLUE = "DISCOVER_CLUE"
    ASK_NPC = "ASK_NPC"
    SUBMIT = "SUBMIT"
