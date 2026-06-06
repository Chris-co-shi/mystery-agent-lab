from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from stery.clue import ClueManager
from stery.domain.models import Character, GameScript, NPCProfile
from stery.domain.state import GameState


class NPCPromptContext(BaseModel):
    """
    NPC Prompt 上下文。

    这是结构化上下文，不是最终 Prompt 文本。

    V0.2.1 设计重点：
    - 让 NPC 更像真实人物：增加语气、情绪、动作、撕逼方式、自保方式。
    - 让 NPC 有边界：明确死者、嫌疑人候选、可怀疑对象、禁止事实类型。
    - 不把 truth / murderer_id / 完整作案链条放进上下文。

    兼容策略：
    - 旧剧本没有 speech_style / allowed_suspicion_targets 等字段也不会崩。
    - 新字段通过 getattr 读取，默认退化为空列表或空字符串。
    """

    model_config = ConfigDict(extra="forbid")

    # 当前 NPC 的公开身份。
    character_id: str
    name: str
    role: str
    public_profile: str

    # 当前 NPC 的私有设定。
    private_background: str
    known_facts: list[str] = Field(default_factory=list)
    secrets: list[str] = Field(default_factory=list)
    lie_rules: list[str] = Field(default_factory=list)
    forbidden_knowledge: list[str] = Field(default_factory=list)
    personality: str = ""

    # V0.2.1：人性化表演字段。
    speech_style: str = ""
    emotion_baseline: str = ""
    emotional_triggers: list[str] = Field(default_factory=list)
    body_language: list[str] = Field(default_factory=list)
    accusation_style: str = ""
    defense_style: str = ""
    relationship_attitudes: list[str] = Field(default_factory=list)
    verbal_tics: list[str] = Field(default_factory=list)

    # V0.2.1：回答边界字段。
    # allowed_suspicion_targets：该 NPC 可以主观怀疑 / 甩锅的对象和理由。
    # forbidden_fact_patterns：该 NPC 不能确认、不能声称看见、不能当事实说出的内容类型。
    allowed_suspicion_targets: list[str] = Field(default_factory=list)
    forbidden_fact_patterns: list[str] = Field(default_factory=list)

    # 世界边界：防止把死者当嫌疑人，防止 NPC 自由扩展嫌疑范围。
    victim_names: list[str] = Field(default_factory=list)
    suspect_candidate_names: list[str] = Field(default_factory=list)

    # 当前交互上下文。
    player_question: str
    recent_question_history: list[str] = Field(default_factory=list)
    available_clue_titles: list[str] = Field(default_factory=list)


class NPCContextBuilder:
    """
    NPC 上下文构造器。

    职责：
    - 找到目标 NPC 的公开角色信息。
    - 找到目标 NPC 的私有设定。
    - 注入玩家当前问题、最近问答历史、当前已公开/已解锁线索标题。
    - 注入 V0.2.1 的表演字段和边界字段。

    不允许注入：
    - truth / truth.summary / murderer_id。
    - 其他 NPC 的 secrets。
    - 其他 NPC 的 private_background。
    - 未解锁线索内容。
    - hidden clue 内容。
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
            private_background=self._read_text(profile, "private_background"),
            known_facts=self._read_list(profile, "known_facts"),
            secrets=self._read_list(profile, "secrets"),
            lie_rules=self._read_list(profile, "lie_rules"),
            forbidden_knowledge=self._read_list(profile, "forbidden_knowledge"),
            personality=self._read_text(profile, "personality"),
            speech_style=self._read_text(profile, "speech_style"),
            emotion_baseline=self._read_text(profile, "emotion_baseline"),
            emotional_triggers=self._read_list(profile, "emotional_triggers"),
            body_language=self._read_list(profile, "body_language"),
            accusation_style=self._read_text(profile, "accusation_style"),
            defense_style=self._read_text(profile, "defense_style"),
            relationship_attitudes=self._read_list(profile, "relationship_attitudes"),
            verbal_tics=self._read_list(profile, "verbal_tics"),
            allowed_suspicion_targets=self._read_list(
                profile,
                "allowed_suspicion_targets",
            ),
            forbidden_fact_patterns=self._read_list(
                profile,
                "forbidden_fact_patterns",
            ),
            victim_names=self._build_victim_names(),
            suspect_candidate_names=self._build_suspect_candidate_names(),
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
        返回最近 5 条问题及其对应 NPC 回答。

        注意：
        - 这里仍然是轻量实现。
        - 后续 GameEvent Runtime 出现后，可以改成按事件检索和压缩。
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

    def _build_victim_names(self) -> list[str]:
        """
        构建死者/受害者列表。

        目的：
        - 明确告诉 NPC：这些人已经死亡，不能被当成当前凶手候选。
        - 解决测试中“把死者当嫌疑人”的问题。
        """
        return [
            character.name
            for character in self.script.characters
            if self._is_victim(character)
        ]

    def _build_suspect_candidate_names(self) -> list[str]:
        """
        构建玩家可理解的嫌疑人候选列表。

        注意：
        - 这里不是让 NPC 必须在候选中选一个。
        - 只是限制 NPC 不要把死者、背景人物、系统对象当成凶手。
        """
        return [
            character.name
            for character in self.script.characters
            if not self._is_victim(character)
            and getattr(character, "is_npc", True)
        ]

    def _is_victim(self, character: Character) -> bool:
        if getattr(character, "is_victim", False):
            return True

        role_text = str(getattr(character, "role", "")).lower()
        return any(
            token in role_text
            for token in ["死者", "受害者", "victim", "deceased"]
        )

    def _read_text(self, obj: Any, field_name: str, default: str = "") -> str:
        value = getattr(obj, field_name, default)

        if value is None:
            return default

        return str(value)

    def _read_list(self, obj: Any, field_name: str) -> list[str]:
        """
        宽容读取 NPCProfile 的列表字段。

        支持：
        - list[str]
        - tuple[str]
        - list[dict]，会格式化成可读文本
        - str，作为单条列表处理

        这样可以在不一次性强改 domain model 的情况下，先让 Prompt 使用新字段。
        """
        value = getattr(obj, field_name, None)

        if value is None:
            return []

        if isinstance(value, str):
            return [value] if value.strip() else []

        if isinstance(value, dict):
            return [self._format_mapping(value)]

        if isinstance(value, (list, tuple, set)):
            result: list[str] = []
            for item in value:
                if item is None:
                    continue

                if isinstance(item, dict):
                    text = self._format_mapping(item)
                else:
                    text = str(item).strip()

                if text:
                    result.append(text)
            return result

        text = str(value).strip()
        return [text] if text else []

    def _format_mapping(self, value: dict) -> str:
        """
        将 dict 型配置格式化成 Prompt 可读文本。

        示例：
        {"target_id": "npc_lu_chen", "reason": "案发当晚出现在 47 层"}
        -> target_id=npc_lu_chen；reason=案发当晚出现在 47 层
        """
        parts: list[str] = []

        for key, item in value.items():
            if item is None:
                continue
            parts.append(f"{key}={item}")

        return "；".join(parts)
