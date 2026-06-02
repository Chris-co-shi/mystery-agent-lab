from stery.application.game_runtime import GameRuntime
from stery.clue import ClueSearchService
from stery.npc.npc_interaction_service import NPCInteractionService
from stery.judge.rule_judge import RuleJudge
from stery.application.session_recorder import SessionRecorder


class MysteryCliApp:
    """
    剧本杀命令行应用。

    职责：
    - 展示菜单
    - 接收玩家输入
    - 调用 GameRuntime / NPCInteractionService / RuleJudge
    - 输出结果

    不负责：
    - LLM 调用细节
    - Prompt 构造
    - 剧本加载
    - Agent 内部逻辑
    """

    def __init__(
            self,
            runtime: GameRuntime,
            npc_interaction_service: NPCInteractionService,
            rule_judge: RuleJudge,
            clue_search_service: ClueSearchService,
            session_recorder: SessionRecorder | None = None,
    ):
        self.runtime = runtime
        self.npc_interaction_service = npc_interaction_service
        self.rule_judge = rule_judge
        self.clue_search_service = clue_search_service
        self.session_recorder = session_recorder or SessionRecorder()

    def run(self) -> None:
        self.runtime.start()

        print("\n==============================")
        print("欢迎进入 AI 剧本杀")
        print("==============================\n")

        self.show_background()
        self.show_help()
        while True:
            raw_input = input("\n> ")
            command = self._normalize_command(raw_input)

            should_continue = self.handle_command(command)

            if not should_continue:
                break

    def show_status(self) -> None:
        print("\n【游戏状态】")

        state = self.runtime.state

        if state is None:
            print("游戏尚未开始。")
            return

        print(f"剧本 ID：{state.script_id}")
        print(f"当前阶段：{state.current_phase.value}")
        print(f"已解锁线索数：{len(state.unlocked_clue_ids)}")
        print(f"提问次数：{len(state.question_history)}")
        print(f"NPC 回答次数：{len(state.answer_history)}")
        print(f"是否已提交最终推理：{'是' if state.final_vote is not None else '否'}")
        print(f"是否已结束：{'是' if state.is_finished else '否'}")

    def show_history(self) -> None:
        print("\n【问答历史】")

        state = self.runtime.state

        if state is None:
            print("游戏尚未开始。")
            return

        if not state.question_history:
            print("暂无问答记录。")
            return

        characters_by_id = {
            character.id: character
            for character in self.runtime.list_characters()
        }

        answers_by_question_id = {
            answer.question_id: answer
            for answer in state.answer_history
        }

        for index, question in enumerate(state.question_history, start=1):
            answer = answers_by_question_id.get(question.question_id)

            npc_display_name = self._format_character_display_name(
                character_id=question.target_character_id,
                characters_by_id=characters_by_id,
            )

            print()
            print(f"[{index}] 询问：{npc_display_name}")
            print(f"玩家：{question.content}")

            if answer is None:
                print("NPC：<暂无回答记录>")
            else:
                print(f"{npc_display_name}：{answer.content}")

    def show_review(self) -> None:
        print("\n【调查摘要】")

        state = self.runtime.state

        if state is None:
            print("游戏尚未开始。")
            return

        characters_by_id = {
            character.id: character
            for character in self.runtime.list_characters()
        }

        answers_by_question_id = {
            answer.question_id: answer
            for answer in state.answer_history
        }


        print(f"已发现线索数：{len(state.unlocked_clue_ids)}")
        print(f"当前总提问次数：{len(state.question_history)}")
        print(f"累计回答次数：{len(state.answer_history)}")

        self._show_review_asked_npcs(
            questions=state.question_history,
            characters_by_id=characters_by_id,
        )

        self._show_review_questions(
            questions=state.question_history,
            answers_by_question_id=answers_by_question_id,
            characters_by_id=characters_by_id,
        )

    def show_background(self) -> None:
        print("\n【案件背景】")
        print(self.runtime.get_background())

    def show_characters(self) -> None:
        print("\n【人物列表】")

        characters = self.runtime.list_characters()

        for index, character in enumerate(characters, start=1):
            print(f"{index}. {character.name}（{character.role}）")
            print(f"   ID：{character.id}")
            print(f"   简介：{character.public_profile}")

    def show_available_clues(self) -> None:
        print("\n【当前可见线索】")

        clues = self.runtime.list_available_clues()

        if not clues:
            print("当前没有可见线索。")
            return

        for index, clue in enumerate(clues, start=1):
            print(f"{index}. {clue.title}")
            print(f"   ID：{clue.id}")
            print(f"   内容：{clue.content}")

    def search_clue(self) -> None:
        print("\n【搜索线索】")
        keyword = input("请输入你要搜索的地点、物品或关键词：").strip()

        if not keyword:
            print("搜索关键词不能为空。")
            return

        try:
            state = self.runtime.state
            if state is None:
                print("游戏尚未开始。")
                return

            result = self.clue_search_service.search(
                state=state,
                keyword=keyword,
            )
        except Exception as exc:
            print(f"搜索失败：{exc}")
            return

        self.show_clue_search_result(result)

    def show_clue_search_result(self, result) -> None:
        print("\n【搜索结果】")
        print(f"关键词：{result.keyword}")
        print(result.message)

        if not result.matched_clues:
            return

        if result.newly_unlocked_clues:
            print("\n【新发现线索】")
            for clue in result.newly_unlocked_clues:
                print(f"- {clue.title}")
                print(f"  ID：{clue.id}")
                print(f"  内容：{clue.content}")

        if result.already_unlocked_clues:
            print("\n【已发现过的线索】")
            for clue in result.already_unlocked_clues:
                print(f"- {clue.title}")
                print(f"  ID：{clue.id}")

    def ask_npc(self) -> None:
        print("\n【询问 NPC】")
        self.show_characters()

        target_character_id = input("\n请输入要询问的 NPC ID：").strip()
        question = input("请输入你的问题：").strip()

        if not target_character_id or not question:
            print("NPC ID 和问题不能为空。")
            return

        try:
            result = self.npc_interaction_service.ask_npc(
                target_character_id=target_character_id,
                question=question,
            )
        except Exception as exc:
            print(f"询问失败：{exc}")
            return

        print("\n【NPC 回答】")
        print(result.npc_answer)

    def submit_final_vote(self) -> bool:
        print("\n【提交最终推理】")

        self.show_characters()
        suspect_character_id = input("\n请输入你认为的凶手 NPC ID：").strip()

        motive = input("请输入作案动机：").strip()
        method = input("请输入作案手法：").strip()

        print("\n请输入关键证据 ID，多个用英文逗号分隔。")
        print("可以先通过菜单 3 查看当前线索。")
        key_evidence_input = input("关键证据 ID：").strip()

        key_evidence = [
            item.strip()
            for item in key_evidence_input.split(",")
            if item.strip()
        ]

        try:
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

        print("\n【推理结果】")
        print(f"是否完全正确：{result.is_correct}")
        print(f"是否命中凶手：{result.matched_murderer}")
        print(f"命中的关键线索：{result.matched_key_clue_ids}")
        print(f"得分：{result.score}")
        print(f"说明：{result.reason}")

        print("\n【真相复盘】")
        print(self.runtime.script.truth.summary)

        self.runtime.finish()
        if self.runtime.state is None:
            print("会话记录生成失败：游戏状态不存在。")
            return True
        record_result = self.session_recorder.save(
            script=self.runtime.script,
            state=self.runtime.state,
        )

        print("\n【会话记录】")
        print(f"JSON：{record_result.json_path}")
        print(f"Markdown：{record_result.markdown_path}")
        return True

    def _normalize_command(self, raw: str) -> str:
        aliases = {
            "help": "/help",
            "status": "/status",
            "background": "/background",
            "characters": "/characters",
            "clues": "/clues",
            "search": "/search",
            "ask": "/ask",
            "history": "/history",
            "submit": "/submit",
            "review": "/review",
            # "close-round": "/close-round",
            # "rounds": "/rounds",
            "summary": "/review",
            "quit": "/quit",
            "exit": "/quit",
        }

        command = raw.strip()
        if not command:
            return ""

        if not command.startswith("/"):
            return aliases.get(command, "")

        return command

    def handle_command(self, command: str) -> bool:
        """
        返回 True：继续游戏
        返回 False：退出游戏
        :param command: 命令
        :return:
        """
        if command == "":
            return False

        if command == '/help':
            self.show_help()
            return True

        if command == '/status':
            self.show_status()
            return True

        if command == '/background':
            self.show_background()
            return True

        if command == '/characters':
            self.show_characters()
            return True

        if command == '/clues':
            self.show_available_clues()
            return True

        if command == '/search':
            self.search_clue()
            return True

        if command == '/ask':
            self.ask_npc()
            return True

        if command == "/history":
            self.show_history()
            return True

        if command == "/review":
            self.show_review()
            return True

        # if command == "/close-round":
        #     self.close_round()
        #     return True
        #
        # if command == "/rounds":
        #     self.show_rounds()
        #     return True

        if command == "/submit":
            return not self.submit_final_vote()

        if command == "/quit":
            print("游戏结束。")
            self.runtime.finish()
            return False

        print("未知命令，请输入 /help 查看可用命令。")
        return True

    def show_help(self) -> None:
        print("\n========== 可用命令 ==========")
        print("/help         查看命令帮助")
        print("/status       查看当前游戏状态")
        print("/background   查看案件背景")
        print("/characters   查看人物列表")
        print("/clues        查看当前线索")
        print("/search       搜索线索")
        print("/ask          询问 NPC")
        print("/history     查看问答历史")
        print("/review       调查摘要")
        print("/submit       提交最终推理")
        print("/quit         退出游戏")
        print("")
        print("==============================")

    def _show_review_asked_npcs(
            self,
            questions,
            characters_by_id: dict,
    ) -> None:
        print("\n【已询问 NPC】")

        if not questions:
            print("暂无已询问 NPC。")
            return

        question_count_by_character_id: dict[str, int] = {}

        for question in questions:
            character_id = question.target_character_id
            question_count_by_character_id[character_id] = (
                    question_count_by_character_id.get(character_id, 0) + 1
            )

        for character_id, count in question_count_by_character_id.items():
            npc_display_name = self._format_character_display_name(
                character_id=character_id,
                characters_by_id=characters_by_id,
            )
            print(f"- {npc_display_name}：{count} 次")

    def _show_review_questions(
            self,
            questions,
            answers_by_question_id: dict,
            characters_by_id: dict,
    ) -> None:
        print("\n【问答记录】")

        if not questions:
            print("暂无问答记录。")
            return

        for index, question in enumerate(questions, start=1):
            answer = answers_by_question_id.get(question.question_id)

            npc_display_name = self._format_character_display_name(
                character_id=question.target_character_id,
                characters_by_id=characters_by_id,
            )

            print()
            print(f"【{index}】 询问 NPC：{npc_display_name}")
            print(f"玩家：{question.content}")

            if answer is None:
                print("NPC：<暂无回答记录>")
            else:
                print(f"NPC：{answer.content}")

    def _format_character_display_name(
            self,
            character_id: str,
            characters_by_id: dict,
    ) -> str:
        character = characters_by_id.get(character_id)

        if character is None:
            return character_id

        return f"{character.name}（{character.id}）"
