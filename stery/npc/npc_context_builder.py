from pydantic import BaseModel, ConfigDict, Field

from stery.clue import ClueManager
from stery.domain.models import Character, GameScript, NPCProfile
from stery.domain.state import GameState


class NPCPromptContext(BaseModel):
    """
    NPC Prompt 上下文。

    注意：
    这是结构化上下文，不是最终 Prompt 文本。
    后续 NPC Agent 会把它转换成真正的 Prompt。
    """

    model_config = ConfigDict(extra="forbid")

    character_id: str
    name: str
    role: str
    public_profile: str

    private_background: str
    known_facts: list[str] = Field(default_factory=list)
    secrets: list[str] = Field(default_factory=list)
    lie_rules: list[str] = Field(default_factory=list)
    forbidden_knowledge: list[str] = Field(default_factory=list)
    personality: str

    player_question: str
    recent_question_history: list[str] = Field(default_factory=list)
    available_clue_titles: list[str] = Field(default_factory=list)


class NPCContextBuilder:
    """
    NPC 上下文构造器。

    职责：
    - 找到目标 NPC 的公开角色信息
    - 找到目标 NPC 的私有设定
    - 注入玩家当前问题
    - 注入最近提问历史
    - 注入当前已解锁线索标题

    不允许注入：
    - truth
    - 其他 NPC 的 secrets
    - 其他 NPC 的 private_background
    - 未解锁线索内容
    - 隐藏线索
    """

    def __init__(self, script: GameScript):
        self.script = script
        self.clue_manager = ClueManager(script)

    def build(
        self,
        state: GameState,
        target_character_id: str,
        player_question: str,
    ) -> NPCPromptContext:
        character = self._find_character(target_character_id)
        profile = self._find_npc_profile(target_character_id)

        available_clues = self.clue_manager.list_available_clues(state)

        return NPCPromptContext(
            character_id=character.id,
            name=character.name,
            role=character.role,
            public_profile=character.public_profile,
            private_background=profile.private_background,
            known_facts=profile.known_facts,
            secrets=profile.secrets,
            lie_rules=profile.lie_rules,
            forbidden_knowledge=profile.forbidden_knowledge,
            personality=profile.personality,
            player_question=player_question,
            recent_question_history=self._build_recent_question_history(state),
            available_clue_titles=[clue.title for clue in available_clues],
        )

    def _find_character(self, character_id: str) -> Character:
        for character in self.script.characters:
            if character.id == character_id:
                return character

        raise ValueError(f"Unknown character_id: {character_id}")

    def _find_npc_profile(self, character_id: str) -> NPCProfile:
        for profile in self.script.npc_profiles:
            if profile.id == character_id:
                return profile

        raise ValueError(f"NPC profile not found for character_id: {character_id}")

    def _build_recent_question_history(self, state: GameState) -> list[str]:
        """
        第一版返回最近 5 条问题及其对应 NPC 回答。

        字段名仍然叫 recent_question_history，是为了减少现阶段改动；
        实际内容已经是最近问答历史。
        """
        recent_questions = state.question_history[-5:]
        answers_by_question_id = {
            answer.question_id: answer
            for answer in state.answer_history
        }

        history: list[str] = []

        for question in recent_questions:
            history.append(f"玩家 -> {question.target_character_id}: {question.content}")

            answer = answers_by_question_id.get(question.question_id)
            if answer is not None:
                history.append(f"{answer.target_character_id} -> 玩家: {answer.content}")

        return history