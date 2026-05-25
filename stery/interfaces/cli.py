from stery.application.game_runtime import GameRuntime
from stery.application.npc_interaction_service import NPCInteractionService
from stery.application.rule_judge import RuleJudge


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
    ):
        self.runtime = runtime
        self.npc_interaction_service = npc_interaction_service
        self.rule_judge = rule_judge

    def run(self) -> None:
        self.runtime.start()

        print("\n==============================")
        print("欢迎进入 AI 剧本杀")
        print("==============================\n")

        self.show_background()

        while True:
            self.show_menu()
            choice = input("请选择操作：").strip()

            if choice == "1":
                self.show_background()
            elif choice == "2":
                self.show_characters()
            elif choice == "3":
                self.show_available_clues()
            elif choice == "4":
                self.ask_npc()
            elif choice == "5":
                self.submit_final_vote()
            elif choice == "0":
                print("游戏结束。")
                break
            else:
                print("无效操作，请重新选择。")

    def show_menu(self) -> None:
        print("\n========== 操作菜单 ==========")
        print("1. 查看案件背景")
        print("2. 查看人物列表")
        print("3. 查看当前线索")
        print("4. 询问 NPC")
        print("5. 提交最终推理")
        print("0. 退出游戏")
        print("==============================")

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

    def submit_final_vote(self) -> None:
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
            return

        if state.final_vote is None:
            print("提交失败：最终推理为空。")
            return

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