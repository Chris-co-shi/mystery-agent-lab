from __future__ import annotations


from stery.domain.enums import CaseActionType
from stery.domain.state import GameState

# 按你的项目实际路径调整：
# 如果 CaseRecord 在 stery.case.case_record，就用下面这行。
# 如果在 stery.domain.state 或其他文件，就改成你的真实路径。
from stery.domain.case_record import CaseRecord
from stery.investigation.investigation_service import InvestigationResult


class CaseRecorder:
    """
    案件记录器。

    负责把玩家行为写入 GameState.case_records。

    注意：
    CaseRecorder 不负责执行业务动作。
    它只负责记录已经发生的行为。

    例如：
    - ClueSearchService / KnownInfoSearchService 负责搜索
    - NPCInteractionService 负责询问 NPC
    - InvestigationService 负责调查对象和解锁线索
    - RuleJudge 负责评分

    CaseRecorder 只把这些结果写成可复盘的 CaseRecord。
    """

    def record_search(
        self,
        *,
        state: GameState,
        target: str,
    ) -> CaseRecord:
        """
        记录一次搜索行为。

        V0.2.0 后，/search 已降级为“已知信息检索”，
        但搜索行为本身仍然应该进入 case_records，
        方便 /review 和 /case 复盘玩家查过什么。
        """

        record = CaseRecord(
            action_type=CaseActionType.SEARCH,
            title=f"搜索：{target}",
            summary=f"玩家搜索了：{target}",
            metadata={
                "target": target,
            },
        )

        state.case_records.append(record)
        state.touch()

        return record

    def record_discovered_clue(
        self,
        *,
        state: GameState,
        clue_id: str,
        clue_name: str,
        source_type: str,
        source_id: str,
        related_question_id: str | None = None,
    ) -> CaseRecord:
        """
        记录一次线索发现行为。

        这个方法主要用于兼容旧流程：
        - V0.1.x 中 /search 可能会直接解锁 LOCKED 线索。
        - V0.2.0 中主要由 /investigate 发现线索。
        - 但为了旧测试、旧导出、后续其他发现入口兼容，仍然保留。

        参数：
            clue_id:
                被发现的线索 ID。

            clue_name:
                被发现的线索标题。

            source_type:
                来源类型，例如 SEARCH / INVESTIGATE / ASK_NPC。

            source_id:
                来源 ID，例如搜索关键词、调查对象 ID、NPC ID。

            related_question_id:
                如果线索来自某次 NPC 问答，可以关联 question_id。
        """

        record = CaseRecord(
            action_type=CaseActionType.DISCOVER_CLUE,
            title=f"发现线索：{clue_name}",
            summary=f"玩家发现了线索：{clue_name}",
            metadata={
                "clue_id": clue_id,
                "clue_name": clue_name,
                "source_type": source_type,
                "source_id": source_id,
                "related_question_id": related_question_id,
            },
        )

        state.case_records.append(record)
        state.touch()

        return record

    def record_ask_npc(
        self,
        *,
        state: GameState,
        npc_id: str,
        npc_name: str,
        question: str,
        answer: str,
    ) -> CaseRecord:
        """
        记录一次询问 NPC 的行为。

        这里只负责记录问答，不负责调用 NPC 或 LLM。
        """

        record = CaseRecord(
            action_type=CaseActionType.ASK_NPC,
            title=f"询问：{npc_name}",
            summary=f"玩家询问了 {npc_name}。",
            metadata={
                "npc_id": npc_id,
                "npc_name": npc_name,
                "question": question,
                "answer": answer,
            },
        )

        state.case_records.append(record)
        state.touch()

        return record

    def record_investigation(
        self,
        *,
        state: GameState,
        result: InvestigationResult,
    ) -> CaseRecord:
        """
        记录一次调查行为。

        InvestigationService 负责调查并返回 InvestigationResult。
        CaseRecorder 负责把 InvestigationResult 写入 case_records。
        """

        newly_discovered_clue_ids = [
            clue.id for clue in result.newly_discovered_clues
        ]
        already_discovered_clue_ids = [
            clue.id for clue in result.already_discovered_clues
        ]

        record = CaseRecord(
            action_type=CaseActionType.INVESTIGATE,
            title=f"调查：{result.target_name}",
            summary=self._build_investigation_summary(
                target_name=result.target_name,
                newly_discovered_clue_ids=newly_discovered_clue_ids,
                already_discovered_clue_ids=already_discovered_clue_ids,
                skipped_hidden_clue_ids=result.skipped_hidden_clue_ids,
            ),
            metadata={
                "target_id": result.target_id,
                "target_name": result.target_name,
                "target_type": result.target_type,
                "newly_discovered_clue_ids": newly_discovered_clue_ids,
                "already_discovered_clue_ids": already_discovered_clue_ids,
                "skipped_hidden_clue_ids": list(result.skipped_hidden_clue_ids),
            },
        )

        state.case_records.append(record)
        state.touch()

        return record

    def record_submit(
        self,
        *,
        state: GameState,
        accused_npc_id: str,
        accused_npc_name: str,
        evidence_clue_ids: list[str],
        reasoning: str,
        judge_result: str,
    ) -> CaseRecord:
        """
        记录玩家提交最终推理的行为。

        这里只记录提交行为，不负责评分。
        评分由 RuleJudge 完成。
        """

        record = CaseRecord(
            action_type=CaseActionType.SUBMIT,
            title="提交最终推理",
            summary=(
                f"玩家指认凶手：{accused_npc_name}；"
                f"提交 {len(evidence_clue_ids)} 条关键证据；"
                f"判定结果：{judge_result}。"
            ),
            metadata={
                "accused_npc_id": accused_npc_id,
                "accused_npc_name": accused_npc_name,
                "evidence_clue_ids": list(evidence_clue_ids),
                "reasoning": reasoning,
                "judge_result": judge_result,
            },
        )

        state.case_records.append(record)
        state.touch()

        return record

    def _build_investigation_summary(
        self,
        *,
        target_name: str,
        newly_discovered_clue_ids: list[str],
        already_discovered_clue_ids: list[str],
        skipped_hidden_clue_ids: list[str],
    ) -> str:
        """
        生成调查记录摘要。

        注意：
        - summary 面向玩家复盘。
        - 不暴露 HIDDEN 线索内容。
        - skipped_hidden_clue_ids 只进入 metadata，不进入 summary。
        """

        if newly_discovered_clue_ids:
            return (
                f"玩家调查了：{target_name}；"
                f"发现 {len(newly_discovered_clue_ids)} 条新线索。"
            )

        if already_discovered_clue_ids:
            return (
                f"玩家调查了：{target_name}；"
                f"没有发现新线索，相关线索此前已知。"
            )

        if skipped_hidden_clue_ids:
            return f"玩家调查了：{target_name}；暂时没有发现可以确认的新线索。"

        return f"玩家调查了：{target_name}；没有发现新的有效线索。"