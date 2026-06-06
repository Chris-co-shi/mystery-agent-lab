"""
CLI submit flow.

这个模块负责 /submit 最终推理提交流程。

设计边界：
- 负责 CLI 输入流程：选择凶手、输入动机、输入手法、选择关键证据。
- 负责提交前展示案件笔记。
- 负责调用 runtime.submit_final_vote。
- 负责调用 rule_judge.evaluate_final_vote。
- 负责记录提交行为。
- 负责保存会话记录。
- 不负责 RuleJudge 内部评分规则。
- 不负责 GameState 底层结构。
"""

from stery.cli.case_presenter import (
    _show_case_discovered_clues,
    _show_case_evidence_candidates,
    _show_case_investigated_targets,
    _show_case_npc_questions,
)
from stery.cli.presenters import (
    _build_clue_title_by_id,
    _format_clue_ids_for_score,
    _show_score_breakdown,
)
from stery.cli.selectors import (
    _prompt_key_evidence_ids,
    _resolve_character_id,
)


class SubmitFlow:
    """
    /submit 最终推理流程。

    Application 只负责命令分发。
    SubmitFlow 负责完整提交交互和提交后的展示、记录、导出。
    """

    def __init__(
            self,
            *,
            runtime,
            rule_judge,
            case_notebook_service,
            case_recorder,
            session_recorder,
    ):
        self.runtime = runtime
        self.rule_judge = rule_judge
        self.case_notebook_service = case_notebook_service
        self.case_recorder = case_recorder
        self.session_recorder = session_recorder

    def run(self) -> bool:
        """
        执行完整 /submit 流程。

        返回：
            True:
                本次 submit 已完成，外层应结束当前游戏循环。
            False:
                提交被取消、输入不完整或提交失败，游戏继续。
        """

        print("\n【提交最终推理】")

        state = self.runtime.state

        if state is None:
            print("游戏尚未开始。")
            return False

        print("\n提交前请先复盘当前案件笔记：")

        # CaseNotebookService 在 __init__ 时已经持有 script，
        # build() 真实签名只需要 state。
        notebook = self.case_notebook_service.build(state)

        self._show_case_notebook(notebook)

        suspect_character_id = self._prompt_suspect_character_id()

        if suspect_character_id is None:
            return False

        motive = input("请输入作案动机：").strip()
        method = input("请输入作案手法：").strip()

        if not motive:
            print("作案动机不能为空。")
            return False

        if not method:
            print("作案手法不能为空。")
            return False

        key_evidence = _prompt_key_evidence_ids(notebook)

        if key_evidence is None:
            return False

        try:
            # 保持你当前 Runtime 的调用方式。
            # 这会更新 state.final_vote。
            state = self.runtime.submit_final_vote(
                suspect_character_id=suspect_character_id,
                motive=motive,
                method=method,
                key_evidence=key_evidence,
            )

        except Exception as exc:
            print(f"提交失败：{exc}")
            return False

        if state.final_vote is None:
            print("提交失败：最终推理为空。")
            return False

        result = self.rule_judge.evaluate_final_vote(state.final_vote)

        self.case_recorder.record_submit(
            state=state,
            accused_npc_id=suspect_character_id,
            accused_npc_name=self._get_character_name(suspect_character_id),
            evidence_clue_ids=key_evidence,
            reasoning=f"动机：{motive}\n手法：{method}",
            judge_result="CORRECT" if result.is_correct else "INCORRECT",
        )

        self._show_evaluation_result(result)

        self._finish_and_save_session(result)

        return True

    def _show_case_notebook(self, notebook) -> None:
        """
        展示提交前案件笔记本。

        这里复用 /case 展示函数，保证 /case 和 /submit 前预览一致。
        """

        print("\n【案件笔记本】")

        clues_by_id = {
            clue.clue_id: clue
            for clue in getattr(notebook, "discovered_clues", [])
        }

        _show_case_discovered_clues(notebook.discovered_clues)
        _show_case_investigated_targets(
            notebook.investigated_targets,
            clues_by_id=clues_by_id,
        )
        _show_case_npc_questions(notebook.npc_questions)
        _show_case_evidence_candidates(notebook.evidence_candidates)

    def _prompt_suspect_character_id(self) -> str | None:
        """
        选择最终指认的凶手。

        支持：
        - 编号
        - 姓名
        - character_id
        """

        candidates = self._get_suspect_candidates()

        if not candidates:
            print("当前没有可提交的嫌疑人。")
            return None

        self._show_suspects(candidates)

        while True:
            raw = input("\n请输入你认为的凶手编号、姓名或 ID：").strip()

            if raw.lower() in {"q", "quit", "exit"} or raw in {"取消", "退出", "返回"}:
                print("已取消本次提交。")
                return None

            if not raw:
                print("凶手不能为空。")
                continue

            suspect_character_id = _resolve_character_id(
                raw=raw,
                candidates=candidates,
            )

            if suspect_character_id is not None:
                return suspect_character_id

            print("请重新输入凶手编号、姓名或 ID。")

    def _get_suspect_candidates(self):
        """
        获取可作为凶手候选的人物。

        规则：
        - 必须是 NPC。
        - 不能是死者 / 受害者。
        """

        characters = self.runtime.list_characters()

        return [
            character
            for character in characters
            if getattr(character, "is_npc", False)
               and not self._is_victim(character)
        ]

    def _show_suspects(self, candidates) -> None:
        """
        展示嫌疑人候选。
        """

        print("\n【嫌疑人列表】")

        for index, character in enumerate(candidates, start=1):
            print(f"{index}. {character.name}（{character.role}）")

            public_profile = getattr(character, "public_profile", "")
            if public_profile:
                print(f"   简介：{public_profile}")

            print(f"   ID：{character.id}")

    def _is_victim(self, character) -> bool:
        """
        判断角色是否是死者 / 受害者。
        """

        if getattr(character, "is_victim", False):
            return True

        role_text = str(getattr(character, "role", ""))

        return (
            "死者" in role_text
            or "受害者" in role_text
            or "victim" in role_text.lower()
        )

    def _get_character_name(self, character_id: str) -> str:
        """
        根据 character_id 获取角色姓名。

        找不到则返回原 ID。
        """

        for character in self.runtime.list_characters():
            if character.id == character_id:
                return character.name

        return character_id

    def _show_evaluation_result(self, result) -> None:
        """
        展示最终推理评分结果。
        """

        print("\n【推理结果】")
        print(f"是否完全正确：{result.is_correct}")
        print(f"是否命中凶手：{result.matched_murderer}")

        clue_title_by_id = _build_clue_title_by_id(self.runtime.script)

        matched_key_clue_titles = _format_clue_ids_for_score(
            getattr(result, "matched_key_clue_ids", []) or [],
            clue_title_by_id,
        )

        print(
            "命中的关键线索："
            f"{'、'.join(matched_key_clue_titles) if matched_key_clue_titles else '无'}"
        )

        print(f"得分：{result.score}/{result.max_score}")
        print(f"说明：{result.reason}")

        _show_score_breakdown(
            result,
            script=self.runtime.script,
        )

        print("\n【真相复盘】")
        print(self.runtime.script.truth.summary)

    def _finish_and_save_session(self, result) -> None:
        """
        结束游戏并保存会话记录。
        """

        self.runtime.finish()

        if self.runtime.state is None:
            print("会话记录生成失败：游戏状态不存在。")
            return

        record_result = self.session_recorder.save(
            script=self.runtime.script,
            state=self.runtime.state,
            judge_result=result,
        )

        print("\n【会话记录】")
        print(f"JSON：{record_result.json_path}")
        print(f"Markdown：{record_result.markdown_path}")


__all__ = ["SubmitFlow"]