from __future__ import annotations

from stery.domain.case_record import CaseRecord
from stery.domain.enums import CaseActionType
from stery.domain.state import GameState


class CaseRecorder:
    """案件调查记录器。"""

    def record_search(
            self,
            state: GameState,
            target: str
    ) -> CaseRecord:
        """记录搜索行为"""

        record = CaseRecord(
            action_type=CaseActionType.SEARCH,
            title=f'搜索:{target}',
            summary=f'搜索:{target}',
            metadata={
                "target": target
            }
        )
        self._append_record(state, record)
        return record

    def record_discovered_clue(
            self,
            state: GameState,
            clue_id: str,
            clue_name: str,
            source_type: str,
            source_id: str | None = None,
            related_question_id: str | None = None
    ) -> CaseRecord:
        """记录发现线索行为"""
        record = CaseRecord(
            action_type=CaseActionType.DISCOVER_CLUE,
            title=f'发现线索：{clue_name}',
            summary=f'玩家发现线索：{clue_name}',
            metadata={
                "clue_id": clue_id,
                "clue_name": clue_name,
                "source_type": source_type,
                "source_id": source_id,
                "related_question_id": related_question_id
            }
        )
        self._append_record(state, record)
        return record

    def record_ask_npc(
            self,
            state: GameState,
            npc_id: str,
            npc_name: str,
            question: str,
            answer: str | None = None
    ) -> CaseRecord:
        """记录与 NPC 交互行为"""
        record = CaseRecord(
            action_type=CaseActionType.ASK_NPC,
            title=f'询问:{npc_name}',
            summary=f'询问:{question}\n回答:{answer}',
            metadata={
                "npc_id": npc_id,
                "npc_name": npc_name,
                "question": question,
                "answer": answer
            }
        )
        self._append_record(state, record)
        return record

    def record_submit(
            self,
            state: GameState,
            accused_npc_id: str,
            accused_npc_name: str,
            evidence_clue_ids: list[str],
            reasoning: str,
            judge_result: str
    ) -> CaseRecord:
        """
        记录最终指控行为
        :param state: 游戏状态属性
        :param accused_npc_id: 指控用户Id
        :param accused_npc_name: 指控用户名称
        :param evidence_clue_ids: 证据集合
        :param reasoning: 推理内容
        :param judge_result: 判断结果
        :return:
        """
        record = CaseRecord(
            action_type=CaseActionType.SUBMIT,
            title=f'最终指控',
            summary=f'最终指控:{accused_npc_name}\n推理:{reasoning}',
            metadata={
                "accused_npc_id": accused_npc_id,
                "accused_npc_name": accused_npc_name,
                "evidence_clue_ids": evidence_clue_ids,
                "reasoning": reasoning,
                "judge_result": judge_result
            }
        )
        self._append_record(state, record)
        return record

    def _append_record(self, state: GameState, record: CaseRecord):
        state.case_records.append(record)
