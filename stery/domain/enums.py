from enum import Enum

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


class CaseActionType(Enum):
    """
    案件记录动作类型。

    这些动作构成玩家在一局游戏中的行为轨迹。
    后续 /review、/case、导出都应基于这些记录展示。
    """

    SEARCH = "SEARCH"
    ASK_NPC = "ASK_NPC"
    DISCOVER_CLUE = "DISCOVER_CLUE"
    SUBMIT = "SUBMIT"

    # V0.2.0 新增：
    # 玩家对地点、尸体、物品执行调查。
    INVESTIGATE = "INVESTIGATE"


class InvestigationTargetType(Enum):
    """
        调查对象类型。

        V0.2.0 MVP 只支持三类：
        - ROOM：地点 / 房间 / 区域
        - BODY：尸体 / 遗体 / 伤口观察
        - ITEM：物品 / 设备 / 文件 / 容器

        当前不做地图系统，不做移动系统。
        type 只是为了让 CLI 和后续 Case Notebook 能更友好地展示调查对象。
    """
    ROOM = "ROOM"
    BODY = "BODY"
    ITEM = "ITEM"
