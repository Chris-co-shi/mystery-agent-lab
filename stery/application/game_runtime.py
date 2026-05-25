from stery.application.clue_manager import ClueManager
from stery.domain.enums import GamePhase
from stery.domain.models import Character, GameScript
from stery.domain.state import FinalVote, GameState, QuestionRecord, NPCAnswerRecord


class GameRuntime:
    """
    最小游戏运行时。

    当前阶段不接 LLM。
    只负责：
    - 启动游戏
    - 获取背景
    - 展示角色
    - 查询线索
    - 记录玩家提问
    - 提交最终推理
    - 结束游戏
    """

    def __init__(self, script: GameScript):
        self.script = script
        self.clue_manager = ClueManager(script)
        self.state: GameState | None = None

    def start(self) -> GameState | None:
        self.state = GameState(
            script_id=self.script.id,
            current_phase=GamePhase.BACKGROUND_INTRO,
            current_round=0,
            unlocked_clue_ids=self.clue_manager.get_initial_unlocked_clue_ids(),
            is_finished=False,
        )
        return self.state

    def get_background(self) -> str:
        self._require_started()
        return self.script.background

    def list_characters(self) -> list[Character]:
        self._require_started()
        return self.script.characters

    def list_available_clues(self):
        state = self._require_started()
        return self.clue_manager.list_available_clues(state)

    def unlock_clue(self, clue_id: str) -> GameState:
        state = self._require_started()
        return self.clue_manager.unlock_clue(state, clue_id)

    def record_question(
            self,
            target_character_id: str,
            question: str,
    ) -> GameState:
        state = self._require_started()

        self._ensure_character_exists(target_character_id)
        self._ensure_question_round_available(state)

        state.question_history.append(
            QuestionRecord(
                target_character_id=target_character_id,
                content=question,
            )
        )
        state.current_round += 1
        state.current_phase = GamePhase.FREE_QUESTION
        state.touch()

        return state

    def record_npc_answer(
            self,
            target_character_id: str,
            answer: str,
            question_id: str | None = None,
    ) -> GameState:
        """
        记录 NPC 回答。

        如果 question_id 为空，则默认绑定到该 NPC 最近一次被问的问题。
        """
        state = self._require_started()

        self._ensure_character_exists(target_character_id)

        actual_question_id = question_id or self._find_latest_question_id(
            state=state,
            target_character_id=target_character_id,
        )

        self._ensure_question_exists(
            state=state,
            question_id=actual_question_id,
            target_character_id=target_character_id,
        )

        state.answer_history.append(
            NPCAnswerRecord(
                question_id=actual_question_id,
                target_character_id=target_character_id,
                content=answer,
            )
        )
        state.touch()

        return state

    def submit_final_vote(
            self,
            suspect_character_id: str,
            motive: str,
            method: str,
            key_evidence: list[str],
    ) -> GameState:
        state = self._require_started()

        self._ensure_character_exists(suspect_character_id)
        self._ensure_clues_exist(key_evidence)

        state.final_vote = FinalVote(
            suspect_character_id=suspect_character_id,
            motive=motive,
            method=method,
            key_evidence=key_evidence,
        )
        state.current_phase = GamePhase.REVEAL_TRUTH
        state.touch()

        return state

    def finish(self) -> GameState:
        state = self._require_started()

        state.current_phase = GamePhase.END
        state.is_finished = True
        state.touch()

        return state

    def _require_started(self) -> GameState:
        if self.state is None:
            raise RuntimeError("Game has not started. Call start() first.")
        return self.state

    def _ensure_character_exists(self, character_id: str) -> None:
        character_ids = {character.id for character in self.script.characters}

        if character_id not in character_ids:
            raise ValueError(f"Unknown character_id: {character_id}")

    def _ensure_clues_exist(self, clue_ids: list[str]) -> None:
        existing_clue_ids = {clue.id for clue in self.script.clues}

        for clue_id in clue_ids:
            if clue_id not in existing_clue_ids:
                raise ValueError(f"Unknown clue_id: {clue_id}")

    def _ensure_question_round_available(self, state: GameState) -> None:
        if state.current_round >= self.script.rules.max_question_rounds:
            raise ValueError(
                f"Question round limit exceeded: "
                f"{state.current_round}/{self.script.rules.max_question_rounds}"
            )

    def _find_latest_question_id(
            self,
            state: GameState,
            target_character_id: str,
    ) -> str:
        for question in reversed(state.question_history):
            if question.target_character_id == target_character_id:
                return question.question_id

        raise ValueError(f"No question found for character_id: {target_character_id}")

    def _ensure_question_exists(
            self,
            state: GameState,
            question_id: str,
            target_character_id: str,
    ) -> None:
        for question in state.question_history:
            if question.question_id == question_id:
                if question.target_character_id != target_character_id:
                    raise ValueError(
                        f"Question target mismatch: "
                        f"question_id={question_id}, "
                        f"expected={target_character_id}, "
                        f"actual={question.target_character_id}"
                    )
                return

        raise ValueError(f"Unknown question_id: {question_id}")
