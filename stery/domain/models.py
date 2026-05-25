from pydantic import BaseModel, ConfigDict, Field

from stery.domain import ClueVisibility, GamePhase


class ScriptBaseModel(BaseModel):
    """
    剧本模型基类。

    extra="forbid" 的作用：
    JSON 中如果出现未定义字段，直接校验失败。
    这样可以避免剧本结构悄悄写错但程序继续运行。
    """
    model_config = ConfigDict(extra="forbid")


class GameRules(ScriptBaseModel):
    """
    游戏规则。
    只表示当前剧本的静态规则，不负责执行规则。
    """
    # 最大提问轮数
    max_question_rounds: int
    # 允许自由提问
    allow_free_question: bool
    # 允许线索搜索
    allow_clue_search: bool
    # 最终投票必填字段
    final_vote: list[str] = Field(
        ...,
        min_length=1,
        description="最终投票必填字段，必须至少包含一个字段"
    )


class Character(ScriptBaseModel):
    """
    剧本中的公开角色信息。

    注意：
    这里只放玩家可见的公开信息。
    NPC 的秘密、已知事实、说谎规则，放到 NPCProfile。
    """
    # 字符 ID
    id: str
    # 角色名
    name: str
    # 角色角色
    role: str
    # 是否是 NPC
    is_npc: bool
    # 公开信息
    public_profile: str


class NPCProfile(ScriptBaseModel):
    """
    NPC 私有设定。

    这是后续 NPC Agent 的上下文来源。
    不能直接暴露给玩家。
    """
    # Id
    id: str
    # 私有背景故事
    private_background: str
    # 已知事实
    known_facts: list[str] = Field(default_factory=list)
    # 私密信息
    secrets: list[str] = Field(default_factory=list)
    # 谎言规则
    lie_rules: list[str] = Field(default_factory=list)
    # 禁止知识
    forbidden_knowledge: list[str] = Field(default_factory=list)
    # 性格
    personality: str


class Clue(ScriptBaseModel):
    """
    线索定义。

    visibility 和 unlock_phase 只表示线索规则，
    具体某一局是否已经解锁，要看 GameState。
    """
    id: str
    # 线索标题
    title: str
    # 线索内容
    content: str
    # 能见状态
    visibility: ClueVisibility
    # 解锁阶段
    unlock_phase: GamePhase
    # 相关角色 ID集合
    related_character_ids: list[str] = Field(default_factory=list)
    # 是否是关键线索
    is_key_clue: bool = False
    # 关键线索关键词
    search_keywords: list[str] = Field(default_factory=list)


class Truth(ScriptBaseModel):
    """
    剧本真相。

    这是高敏感信息。
    第一版只有 Host / Judge 可以读取完整 Truth。
    """
    id: str
    # 动机
    motive: str
    # 方法
    method: str
    # 关键线索 ID集合
    key_clue_ids: list[str] = Field(default_factory=list)
    # 概要
    summary: str

class TimelineEvent(ScriptBaseModel):
    """
    剧本时间线事件。

    is_public=true 的事件可以在合适阶段展示给玩家。
    is_public=false 的事件只给 Host / Judge 使用。
    """
    #  时间
    time: str
    id: str
    # 事件
    event: str
    # 是否公开
    is_public: bool

class GameScript(ScriptBaseModel):
    """
    完整剧本定义。

    GameScript 是静态数据，不表示一局游戏的运行状态。
    """
    id: str
    # 标题
    title: str
    # 版本
    version: str
    # 背景
    background: str
    # 规则
    rules: GameRules
    characters: list[Character] = Field(default_factory=list)
    npc_profiles: list[NPCProfile] = Field(default_factory=list)
    clues: list[Clue] = Field(default_factory=list)
    truth: Truth
    timeline: list[TimelineEvent] = Field(default_factory=list)
