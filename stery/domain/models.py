from typing import Any

from pydantic import BaseModel, ConfigDict, Field, model_validator, AliasChoices

from stery.domain import ClueVisibility, GamePhase
from stery.domain.enums import InvestigationTargetType


class ScriptBaseModel(BaseModel):
    """
    剧本模型基类。

    extra="forbid" 的作用：
    JSON 中如果出现未定义字段，直接校验失败。
    这样可以避免剧本结构悄悄写错但程序继续运行。
    """
    model_config = ConfigDict(extra="forbid")


class ScoringRule(ScriptBaseModel):
    """
    剧本评分权重配置
    这个类只表示GameScript JSON中rules.scoring的数据结构

    为什么不直接使用 stery.judge.scoring.ScoringConfig？

    因为：
    - domain.models 是剧本协议层。
    - stery.judge.scoring 是判案评分实现层。
    - domain 不应该依赖 judge。
    - 正确依赖方向应该是 judge 依赖 domain，而不是 domain 依赖 judge。

    实际评分仍然由：
    - stery.judge.scoring.ScoringConfig
    - stery.judge.scoring.build_score_breakdown
    完成。
    """
    # 凶手判断分
    murderer_score: int = 40
    # 关键证据分
    key_evidence_score: int = 30
    # 作案动机分
    motive_score: int = 15
    # 作案手法分
    method_score: int = 15


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
    # V0.2.0 新增：评分配置。
    #
    # 这里必须用 default_factory，而不是 scoring: ScoringRule = ScoringRule()
    # 原因：
    # - Pydantic 模型字段建议使用 Field(default_factory=...)
    # - 避免默认对象被多个实例共享
    # - 语义上也更明确：每个 GameRules 都有自己的默认评分配置
    scoring: ScoringRule = Field(default_factory=ScoringRule)


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
    # V0.2.0 剧本生成规则中的公开角色字段。
    # 不涉及私密信息，可以放在 Character。
    is_victim: bool = False
    relationship_to_victim: str = ""


class NPCProfile(ScriptBaseModel):
    """
    NPC 私有设定。

    这是后续 NPC Agent 的上下文来源。
    不能直接暴露给玩家。
    """
    # Id
    id: str = Field(validation_alias=AliasChoices("id", "character_id"))
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
    # V0.2.0 生成剧本里已经存在这些 NPC 私有字段。
    # 它们暂时只作为数据承载，不在当前 TASK 中执行逻辑。
    alibi_claim: str = ""
    possible_motive: str = ""


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
    unlock_phase: GamePhase = GamePhase.START
    # 相关角色 ID集合
    related_character_ids: list[str] = Field(default_factory=list)
    # 是否是关键线索
    is_key_clue: bool = False
    # 关键线索关键词
    search_keywords: list[str] = Field(default_factory=list)
    # V0.2.0 可选元数据。
    # 当前只加载，不强依赖。
    importance: str | None = None
    clue_type: str | None = None
    related_target_ids: list[str] = Field(default_factory=list)
    reasoning_tags: list[str] = Field(default_factory=list)


class InvestigationTarget(ScriptBaseModel):
    """
       V0.2.0 调查对象定义。

       InvestigationTarget 是玩家可以主动调查的对象，
       例如：
       - 书房
       - 死者尸体
       - 摔碎的红酒杯
       - 加密终端
       - 门禁记录仪

       它只描述“静态配置”：
       - 这个对象叫什么
       - 属于什么类型
       - 玩家看到的描述是什么
       - 哪些关键词可以帮助玩家选择它
       - 调查它可以发现哪些线索

       它不负责：
       - 判断玩家是否已经调查过
       - 解锁线索
       - 写入 case_records
       - 生成 CLI 展示文本

       这些留给后续 InvestigationService 和 CLI 层。
    """
    # 调查对象 ID，内部引用使用。
    # 玩家层后续应展示 name，不要求玩家输入 id。
    id: str
    # 玩家可见名称。
    name: str
    # 调查对象类型，只允许 ROOM / BODY / ITEM。
    type: InvestigationTargetType
    # 玩家调查前或调查时看到的描述。
    description: str
    # 搜索 / 选择辅助关键词。
    #
    # 例如玩家输入“尸体”，可以匹配到 name="顾明远的尸体"。
    # V0.2.0 这里只保存数据，不实现匹配逻辑。
    search_keywords: list[str] = Field(default_factory=list)
    # 调查该对象可以发现的线索 ID。
    #
    # 注意：
    # - 这里仅表示“这个对象关联哪些可发现线索”。
    # - 是否重复解锁、是否过滤 HIDDEN，留给 InvestigationService。
    discoverable_clue_ids: list[str] = Field(default_factory=list)


class Truth(ScriptBaseModel):
    """
    剧本真相。

    V0.2.0 新增：
    - murderer_id：明确表示真凶角色 ID。
    - motive_keywords：用于动机确定性评分。
    - method_keywords：用于手法确定性评分。

    兼容策略：
    - 旧剧本使用 truth.id 表示真凶。
    - 新剧本使用 truth.murderer_id。
    - 当前 id 允许为空，RuleJudge 使用 murderer_id or id。
    """

    # 旧字段。旧剧本中它实际承担“真凶 ID”作用。
    # 新剧本可以不提供 id，只提供 murderer_id。
    id: str | None = None

    murderer_id: str | None = None

    motive: str
    method: str

    # 内部 canonical 仍然叫 key_clue_ids。
    # 兼容新生成剧本中的 key_evidence_ids。
    key_clue_ids: list[str] = Field(
        default_factory=list,
        validation_alias=AliasChoices("key_clue_ids", "key_evidence_ids"),
    )

    motive_keywords: list[str] = Field(default_factory=list)
    method_keywords: list[str] = Field(default_factory=list)

    # 旧模型要求 summary，新生成剧本更常用 explanation。
    # 当前允许 summary 缺省，并在 validator 中尝试用 explanation 填充。
    summary: str = ""
    explanation: str | None = None

    # 密室机制是生成规则中的可选结构化说明。
    # 当前模型接收，但 RuleJudge 暂不依赖。
    locked_room_mechanism: dict[str, Any] | None = None

    @model_validator(mode="after")
    def fill_summary_from_explanation(self) -> "Truth":
        """
        如果新剧本只提供 explanation，没有 summary，
        则用 explanation 填充 summary。

        这样旧代码继续读取 truth.summary 时不会拿到空值。
        """

        if not self.summary and self.explanation:
            self.summary = self.explanation

        return self


class TimelineEvent(ScriptBaseModel):
    """
    剧本时间线事件。

    时间线是剧本静态信息，用于表达案发前后的事件顺序。

    兼容策略：
    - 旧剧本可能使用 id 表示时间线事件 ID。
    - 新生成剧本更常使用 character_id 表示该事件关联的角色。
    - 当前 V0.2.0 运行逻辑暂时不依赖 timeline.id。
    - 因此 id 和 character_id 都先设为可选字段。

    后续如果要做时间线推理、案件笔记本或 Validator，
    可以再要求：
    - 公开时间线是否必须有 id
    - character_id 是否必须存在于 characters
    - 关键事件是否必须可由线索证明
    """
    # 事件发生时间，例如 "18:10"。
    time: str
    # 事件内容。
    event: str
    # 是否公开。
    # true 的事件可以展示给玩家；
    # false 的事件只给 Host / Judge / Validator 使用。
    is_public: bool
    # 旧剧本兼容字段：时间线事件 ID。
    # 新生成剧本可以不提供。
    id: str | None = None
    # V0.2.0 生成剧本常用字段：
    # 表示该事件关联的角色 ID。
    character_id: str | None = None


class GameScript(ScriptBaseModel):
    """
    完整剧本定义。

    GameScript 是静态数据，不表示一局游戏的运行状态。
    """

    id: str
    title: str
    version: str
    background: str
    rules: GameRules

    # V0.2.0 生成规则中的顶层描述字段。
    # 当前只承载，不参与运行逻辑。
    genre: str | None = None
    difficulty: str | None = None
    estimated_minutes: int | None = None

    characters: list[Character] = Field(default_factory=list)
    npc_profiles: list[NPCProfile] = Field(default_factory=list)
    clues: list[Clue] = Field(default_factory=list)
    investigation_targets: list[InvestigationTarget] = Field(default_factory=list)
    truth: Truth
    timeline: list[TimelineEvent] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_references(self) -> "GameScript":
        """
        最小引用一致性校验。

        当前只做模型层能稳定保障的检查：
        1. investigation_targets.discoverable_clue_ids 必须存在于 clues。
        2. truth.key_clue_ids 必须存在于 clues。
        3. truth.murderer_id 或兼容字段 truth.id 必须存在于 characters。

        当前不做：
        - HIDDEN 是否能被普通调查发现
        - LOCKED 是否必须绑定 investigation_targets
        - clue_type / reasoning_tags 语义校验
        - NPCProfile 是否完全覆盖所有 NPC
        """

        clue_ids = {clue.id for clue in self.clues}
        character_ids = {character.id for character in self.characters}

        for target in self.investigation_targets:
            for clue_id in target.discoverable_clue_ids:
                if clue_id not in clue_ids:
                    raise ValueError(
                        f"InvestigationTarget {target.id} references unknown clue_id: {clue_id}"
                    )

        for clue_id in self.truth.key_clue_ids:
            if clue_id not in clue_ids:
                raise ValueError(
                    f"Truth references unknown key clue_id: {clue_id}"
                )

        expected_murderer_id = self.truth.murderer_id or self.truth.id
        if expected_murderer_id and expected_murderer_id not in character_ids:
            raise ValueError(
                f"Truth references unknown murderer_id: {expected_murderer_id}"
            )

        return self
