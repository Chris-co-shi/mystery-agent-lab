from stery.application.game_runtime import GameRuntime
from stery.case.case_notebook_service import CaseNotebookService
from stery.case.known_info_search_service import KnownInfoSearchService
from stery.cli.ask_flow import  AskFlow
from stery.clue import ClueSearchService
from stery.investigation.investigation_service import InvestigationService
from stery.npc.npc_interaction_service import NPCInteractionService
from stery.judge.rule_judge import RuleJudge
from stery.application.session_recorder import SessionRecorder
from stery.case.case_recorder import CaseRecorder

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
    show_known_info_search_result,
)
from stery.cli.review_presenter import (
    _get_record_metadata,
    _normalize_action_type,
    _show_clue_id_list,
)
from stery.cli.selectors import (
    _prompt_key_evidence_ids,
    _resolve_character_id,
)

def _part_get(part, key: str, default=None):
    """
    兼容读取 dict / object 两种评分项结构。
    """

    if part is None:
        return default

    if isinstance(part, dict):
        return part.get(key, default)

    return getattr(part, key, default)

def show_help() -> None:
    """
    展示玩家可用命令。

    命令分组原则：
    1. 案件基础信息：帮助玩家理解故事。
    2. 玩家行动：会改变游戏状态。
    3. 已知信息复盘：只读视图，帮助玩家整理推理。
    4. 状态与流程：查看进度、提交、退出。

    /history 不再作为玩家核心命令展示。
    兼容旧输入时，/history 会被映射到 /review。
    """

    print("\n========== 可用命令 ==========")

    print("\n【案件信息】")
    print("/background   查看案件背景")
    print("/characters   查看人物列表")

    print("\n【玩家行动】")
    print("/investigate  调查地点、尸体或物品")
    print("/ask          询问 NPC")

    print("\n【已知信息】")
    print("/clues        查看已发现线索")
    print("/search       检索已知信息")
    print("/case         查看案件笔记本")
    print("/review       查看调查记录")

    print("\n【流程】")
    print("/status       查看当前进度")
    print("/submit       提交最终推理")
    print("/help         查看命令帮助")
    print("/quit         退出游戏")

    print("\n==============================")


def _normalize_command(raw: str) -> str:
    """
    规范化玩家输入的命令。

    设计说明：
    - 玩家可以输入 /command，也可以输入不带斜杠的 command。
    - 中文别名只保留少量高频入口，避免命令体系继续膨胀。
    - /history 已降级为兼容命令，统一转到 /review。
    """

    aliases = {
        "help": "/help",
        "status": "/status",
        "background": "/background",
        "characters": "/characters",
        "clues": "/clues",
        "search": "/search",
        "investigate": "/investigate",
        "调查": "/investigate",
        "ask": "/ask",
        "history": "/review",
        "历史": "/review",
        "review": "/review",
        "summary": "/review",
        "case": "/case",
        "notebook": "/case",
        "笔记": "/case",
        "submit": "/submit",
        "quit": "/quit",
        "exit": "/quit",
    }

    command = raw.strip()

    if not command:
        return ""

    # 不带 / 的输入，按别名解析。
    # 如果不是已知别名，也原样返回给 handle_command，让它走“未知命令”提示。
    # 不要返回空字符串，否则玩家输错命令会被误判为退出。
    if not command.startswith("/"):
        return aliases.get(command, command)

    # 带 / 的旧命令兼容。
    if command == "/history":
        return "/review"

    return command


class Application:
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
        self.case_recorder = CaseRecorder()
        # V0.2.0 新增：调查服务。
        #
        # 这里直接用 runtime.script 初始化，避免外部调用方现在就必须改构造参数。
        # 后续如果 CLI 依赖继续变多，可以再考虑引入 CliDependencies。
        self.investigation_service = InvestigationService(runtime.script)
        # V0.2.0 新增：
        # /search 降级为“已知信息检索”，不再负责解锁 LOCKED 线索。
        self.known_info_search_service = KnownInfoSearchService(runtime.script)
        # V0.2.0 新增：
        # /case 案件笔记本服务，只读 GameState，不修改游戏状态。
        self.case_notebook_service = CaseNotebookService(runtime.script)

    def run(self) -> None:
        self.runtime.start()

        print("\n==============================")
        print("欢迎进入 AI 剧本杀")
        print("==============================\n")

        self.show_background()
        show_help()
        while True:
            raw_input = input("\n> ")
            command = _normalize_command(raw_input)

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

    def show_investigation_targets(self) -> None:
        """
        展示当前剧本中的可调查对象。

        玩家层不展示内部 ID。
        原因：
        - ID 是系统内部关联字段。
        - 普通玩家应该通过编号 / 名称 / 关键词选择。
        - ID 仍然允许作为输入，但不主动暴露在界面上。
        """

        print("\n【可调查对象】")

        targets = self.investigation_service.list_targets()

        if not targets:
            print("当前剧本暂无可调查对象。")
            return

        for index, target in enumerate(targets, start=1):
            target_type = self._format_enum_value(target.type)

            print(f"{index}. {target.name}（{target_type}）")
            print(f"   描述：{target.description}")

            if target.search_keywords:
                print(f"   关键词：{'、'.join(target.search_keywords)}")

    def investigate_target(self) -> None:
        """
        执行一次调查。

        V0.2.0 交互规则：
        - 玩家先看到可调查对象列表。
        - 玩家可以输入编号、名称、关键词。
        - 如果关键词匹配多个对象，提示候选编号，并继续输入。
        - 不把内部 ID 暴露给普通玩家。
        """

        print("\n【调查对象】")

        state = self.runtime.state

        if state is None:
            print("游戏尚未开始。")
            return

        targets = self.investigation_service.list_targets()

        if not targets:
            print("当前剧本暂无可调查对象。")
            return

        self.show_investigation_targets()

        target_id: str | None = None

        while target_id is None:
            raw_target = input("\n请输入要调查的对象编号或名称（输入 q 取消）：").strip()

            if raw_target.lower() in {"q", "quit", "exit"} or raw_target in {"取消", "退出"}:
                print("已取消调查。")
                return

            if not raw_target:
                print("调查对象不能为空。")
                continue

            target_id = self._resolve_investigation_target_id(
                raw=raw_target,
                targets=targets,
            )

            if target_id is None:
                print("请重新输入调查对象编号或名称。")

        try:
            result = self.investigation_service.investigate(
                state=state,
                target_id=target_id,
            )

            self.case_recorder.record_investigation(
                state=state,
                result=result,
            )

        except Exception as exc:
            print(f"调查失败：{exc}")
            return

        self.show_investigation_result(result)

    def show_review(self) -> None:
        """
        展示调查记录。

        /review 的职责边界：
        - 回答“我之前做过什么？”
        - 按行动发生顺序展示 case_records。
        - 可以展示行动附带的关键结果，例如本次调查发现了哪些线索。
        - 不做推理归纳，不替代 /case。

        和 /case 的区别：
        - /review：时间线式行动记录。
        - /case：结构化案件笔记。
        """

        print("\n【调查记录】")

        state = self.runtime.state

        if state is None:
            print("游戏尚未开始。")
            return

        if not state.case_records:
            print("暂无调查记录。")
            return

        # 只把玩家已可见线索放进映射，避免 review 误泄露未发现线索。
        clues_by_id = {
            clue.id: clue
            for clue in self.runtime.list_available_clues()
        }

        for index, record in enumerate(state.case_records, start=1):
            print()
            print(f"{index}. {record.title}")

            summary = getattr(record, "summary", "")
            if summary:
                print(f"   {summary}")

            self._show_review_record_details(
                record=record,
                clues_by_id=clues_by_id,
            )

    def show_case_notebook(self) -> None:
        """
        展示案件笔记本 MVP。

        /review 偏过程流水；
        /case 偏提交前整理视图。
        """

        print("\n【案件笔记本】")

        state = self.runtime.state

        if state is None:
            print("游戏尚未开始。")
            return

        notebook = self.case_notebook_service.build(state)

        # 仅使用 notebook 中已经发现的线索建立索引。
        # 这样可以在展示“已调查对象”时显示线索标题，同时不会泄露未发现线索。
        notebook_clues_by_id = {
            clue.clue_id: clue
            for clue in notebook.discovered_clues
        }

        _show_case_discovered_clues(notebook.discovered_clues)
        _show_case_investigated_targets(
            notebook.investigated_targets,
            clues_by_id=notebook_clues_by_id,
        )
        _show_case_npc_questions(notebook.npc_questions)
        _show_case_evidence_candidates(notebook.evidence_candidates)

    def show_background(self) -> None:
        print("\n【案件背景】")
        print(self.runtime.get_background())

    def show_characters(self) -> None:
        """
        展示剧本中的全部玩家可见人物。

        这个命令用于“认识案件人物”，不是“选择可询问 NPC”。
        因此它可以展示死者、受害者、背景人物等公开角色。

        注意：
        - /characters 只展示 public_profile。
        - 不展示 npc_profiles 中的秘密、动机、撒谎规则等私有信息。
        - /ask 不能直接复用这个列表，否则会把死者也展示成可询问对象。
        """

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
        """
        搜索已知信息。

        V0.2.0 语义：
        - /search 是“检索已知信息”，不是“发现新线索”。
        - 新线索只能通过 /investigate 或后续明确设计过的行动产生。
        - /search 可以被记录到 case_records，供 /review 回看玩家做过什么。
        - 但 SEARCH 行为记录不能污染检索结果本身。

        实现细节：
        - 先检索，再记录搜索行为，避免当前搜索立即命中自己。
        - 展示层仍会过滤历史 SEARCH 记录，防止旧搜索记录污染后续搜索。
        """

        print("\n【检索已知信息】")
        keyword = input("请输入你要检索的关键词：").strip()

        if not keyword:
            print("搜索关键词不能为空。")
            return

        state = self.runtime.state

        if state is None:
            print("游戏尚未开始。")
            return

        try:
            result = self.known_info_search_service.search(
                state=state,
                keyword=keyword,
            )

        except Exception as exc:
            print(f"检索失败：{exc}")
            return

        show_known_info_search_result(result)

        # 记录搜索行为必须放在检索之后。
        # 否则本次搜索会把“玩家搜索了：xxx”也搜出来。
        try:
            self.case_recorder.record_search(
                state=state,
                target=keyword,
            )
        except Exception as exc:
            # 记录失败不应该影响玩家看到检索结果。
            # 这里给出提示，但不终止游戏。
            print(f"\n提示：搜索记录写入失败：{exc}")

    def ask_npc(self) -> None:
        """
        进入 NPC 询问模式。

        V0.2.2 交互设计：
        - 玩家进入 /ask 后，先选择一个可询问 NPC。
        - 选择后进入连续问答模式。
        - 在连续问答中可以：
            1. 直接输入问题，继续问当前 NPC。
            2. 输入 @NPC姓名 / @NPC编号 / @NPC ID 快速切换 NPC。
            3. 输入 /switch 手动切换 NPC。
            4. 输入 /list 查看可询问 NPC。
            5. 输入 /help 查看询问模式帮助。
            6. 输入 q / quit / exit / 返回 / 退出 返回主命令。

        注意：
        - /ask 模式只处理 NPC 问答。
        - 不在 /ask 内部嵌套 /investigate、/search、/case、/submit 等主命令。
        - 这样可以避免 CLI 变成复杂子系统。
        """

        AskFlow(
            runtime=self.runtime,
            npc_interaction_service=self.npc_interaction_service,
            case_recorder=self.case_recorder,
        ).run()

    def submit_final_vote(self) -> bool:
        """
        提交最终推理。

        V0.2.0 改造点：
        1. 提交前先展示案件笔记本，帮助玩家复盘。
        2. 凶手选择不再强制输入 NPC ID，支持编号 / 名称 / ID。
        3. 关键证据选择不再强制复制 clue_id，支持编号 / 标题 / ID。
        4. 提交后展示 score_breakdown，让玩家理解每部分得分来源。

        返回：
            True  表示本次 submit 流程执行完毕，外层应结束游戏。
            False 表示提交失败或被中断，游戏继续。
        """

        print("\n【提交最终推理】")

        state = self.runtime.state

        if state is None:
            print("游戏尚未开始。")
            return False

        # 1. 提交前展示案件笔记本。
        #
        # 这一步解决玩家提交前看不到线索、问答和调查记录的问题。
        # 注意：show_case_notebook() 只读状态，不会修改 GameState。
        print("\n提交前请先复盘当前案件笔记：")
        self.show_case_notebook()

        # 2. 构建 notebook，后续用于证据候选选择。
        notebook = self.case_notebook_service.build(state)

        # 3. 选择凶手。
        suspect_character_id = self._prompt_suspect_character_id()

        if suspect_character_id is None:
            return False

        # 4. 输入动机和手法。
        motive = input("请输入作案动机：").strip()
        method = input("请输入作案手法：").strip()

        if not motive:
            print("作案动机不能为空。")
            return False

        if not method:
            print("作案手法不能为空。")
            return False

        # 5. 选择关键证据。
        key_evidence = _prompt_key_evidence_ids(notebook)

        if key_evidence is None:
            return False

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

        self.case_recorder.record_submit(
            state=state,
            accused_npc_id=suspect_character_id,
            accused_npc_name=self._get_character_name(suspect_character_id),
            evidence_clue_ids=key_evidence,
            reasoning=f"动机：{motive}\n手法：{method}",
            judge_result="CORRECT" if result.is_correct else "INCORRECT",
        )

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

        self.runtime.finish()

        if self.runtime.state is None:
            print("会话记录生成失败：游戏状态不存在。")
            return True

        record_result = self.session_recorder.save(
            script=self.runtime.script,
            state=self.runtime.state,
            judge_result=result,
        )

        print("\n【会话记录】")
        print(f"JSON：{record_result.json_path}")
        print(f"Markdown：{record_result.markdown_path}")

        return True

    def handle_command(self, command: str) -> bool:
        """
        返回 True：继续游戏
        返回 False：退出游戏
        :param command: 命令
        :return:
        """
        if command == "":
            print("请输入命令，或输入 /help 查看可用命令。")
            return True

        if command == '/help':
            show_help()
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

        if command == '/investigate':
            self.investigate_target()
            return True

        if command == '/ask':
            self.ask_npc()
            return True

        if command == "/review":
            self.show_review()
            return True

        if command == "/case":
            self.show_case_notebook()
            return True

        if command == "/submit":
            return not self.submit_final_vote()

        if command == "/quit":
            print("游戏结束。")
            self.runtime.finish()
            return False

        print("未知命令，请输入 /help 查看可用命令。")
        return True

    def _show_review_record_details(
            self,
            *,
            record,
            clues_by_id: dict,
    ) -> None:
        """
        展示单条 CaseRecord 的结构化详情。

        这一步是 /review 从“纯 summary 文本”升级为“可复盘行动记录”的关键：
        - INVESTIGATE：展示调查对象和发现的线索标题。
        - SEARCH：展示搜索关键词，但不把搜索记录混进 /search 结果。
        - ASK_NPC：展示问谁、问了什么、回答摘要。
        - SUBMIT：展示提交对象和证据。

        兼容性原则：
        - metadata 缺失时不报错。
        - 未识别的 action_type 只展示 record.summary。
        """

        action_type = _normalize_action_type(record)
        metadata = _get_record_metadata(record)

        if "INVESTIGATE" in action_type:
            target_name = metadata.get("target_name")
            target_type = metadata.get("target_type")

            if target_name:
                if target_type:
                    print(f"   调查对象：{target_name}（{target_type}）")
                else:
                    print(f"   调查对象：{target_name}")

            _show_clue_id_list(
                label="新发现线索",
                clue_ids=list(metadata.get("newly_discovered_clue_ids", [])),
                clues_by_id=clues_by_id,
            )
            _show_clue_id_list(
                label="已知线索",
                clue_ids=list(metadata.get("already_discovered_clue_ids", [])),
                clues_by_id=clues_by_id,
            )
            return

        if "SEARCH" in action_type:
            keyword = metadata.get("keyword") or metadata.get("target")
            result_count = metadata.get("result_count")

            if keyword:
                print(f"   搜索关键词：{keyword}")

            if result_count is not None:
                print(f"   命中结果：{result_count} 条")
            return

        if "ASK_NPC" in action_type:
            npc_name = metadata.get("npc_name") or metadata.get("target_character_name")
            npc_id = metadata.get("npc_id") or metadata.get("target_character_id")
            question = metadata.get("question")
            answer = metadata.get("answer")

            if npc_name:
                if npc_id:
                    print(f"   询问对象：{npc_name}（{npc_id}）")
                else:
                    print(f"   询问对象：{npc_name}")

            if question:
                print(f"   问：{question}")

            if answer:
                print(f"   答：{answer}")
            return

        if "SUBMIT" in action_type:
            accused_name = metadata.get("accused_npc_name")
            accused_id = metadata.get("accused_npc_id")
            evidence_clue_ids = list(metadata.get("evidence_clue_ids", []))
            judge_result = metadata.get("judge_result")

            if accused_name:
                if accused_id:
                    print(f"   指认凶手：{accused_name}（{accused_id}）")
                else:
                    print(f"   指认凶手：{accused_name}")

            _show_clue_id_list(
                label="提交证据",
                clue_ids=evidence_clue_ids,
                clues_by_id=clues_by_id,
            )

            if judge_result:
                print(f"   判定结果：{judge_result}")

    def _get_character_name(self, character_id: str) -> str:
        for character in self.runtime.list_characters():
            if character.id == character_id:
                return character.name

        return character_id

    def _is_victim_character(self, character) -> bool:
        """
        判断角色是否为受害者 / 死者。

        优先使用模型字段 is_victim。
        同时兼容旧剧本：有些 Character 可能还没有 is_victim 字段，
        但 role 文案中包含“死者”。CLI 层只做保守过滤，避免把死者展示为可询问对象。
        """

        if getattr(character, "is_victim", False):
            return True

        role = str(getattr(character, "role", ""))
        return "死者" in role or "受害者" in role

    def _get_npc_profile_character_ids(self) -> set[str]:
        """
        从 GameScript.npc_profiles 中提取真正有 NPC Profile 的 character_id。

        /ask 的服务层依赖 npc_profile：
        - 有 npc_profile：可以问。
        - 没有 npc_profile：不能问，否则会出现 NPC profile not found。

        这里做了字段兼容：
        - 标准字段优先：character_id。
        - 兼容可能的旧字段：npc_id / id。

        注意：
        - 这个方法只返回 ID，不暴露 profile 里的秘密字段。
        - 如果某个 fallback 字段不是 character_id，后续和 characters 对不上，也不会被展示。
        """

        profiles = getattr(self.runtime.script, "npc_profiles", None) or []
        character_ids: set[str] = set()

        for profile in profiles:
            for field_name in ("character_id", "npc_id", "id"):
                value = getattr(profile, field_name, None)

                if isinstance(value, str) and value.strip():
                    character_ids.add(value.strip())

        return character_ids

    def _prompt_suspect_character_id(self) -> str | None:
        """
        让玩家选择最终怀疑的凶手。

        支持输入：
        - 编号：1
        - 角色名：祁曼殊
        - 角色 ID：npc_qi_manshu

        当前默认只展示 NPC 作为嫌疑人候选。
        死者或非 NPC 角色通常不作为最终凶手提交候选。
        """

        candidates = self._get_suspect_candidates()

        if not candidates:
            print("当前没有可提交的嫌疑人。")
            return None

        print("\n【嫌疑人列表】")

        for index, character in enumerate(candidates, start=1):
            print(f"{index}. {character.name}（{character.role}）")
            print(f"   简介：{character.public_profile}")
            print(f"   ID：{character.id}")

        raw = input("\n请输入你认为的凶手编号、姓名或 ID：").strip()

        if not raw:
            print("凶手不能为空。")
            return None

        return _resolve_character_id(
            raw=raw,
            candidates=candidates,
        )

    def _get_suspect_candidates(self):
        """
        获取可提交凶手候选。

        当前策略：
        - 优先展示 is_npc=True 的角色。
        - 排除 is_victim=True 的角色。
        - 如果没有 NPC，则退回展示所有非受害者角色。

        这样既适配当前剧本，也避免普通玩家把死者作为凶手候选。
        """

        characters = self.runtime.list_characters()

        candidates = [
            character
            for character in characters
            if getattr(character, "is_npc", False)
               and not getattr(character, "is_victim", False)
        ]

        if candidates:
            return candidates

        return [
            character
            for character in characters
            if not getattr(character, "is_victim", False)
        ]

    def _resolve_investigation_target_id(self, raw: str, targets) -> str | None:
        """
        将玩家输入解析为 investigation_target_id。

        支持：
        1. 编号：1、2、3
        2. 名称：沈维舟的尸体
        3. 关键词：尸体、注入器、终端
        4. ID：target_body，兼容开发调试，但界面不主动展示 ID

        如果匹配多个对象，不自动猜测，提示玩家继续输入编号。
        """

        value = raw.strip()

        if not value:
            return None

        # 1. 编号选择。
        if value.isdigit():
            index = int(value)

            if 1 <= index <= len(targets):
                return targets[index - 1].id

            print(f"无效编号：{value}。请输入 1 到 {len(targets)} 之间的数字。")
            return None

        # 2. 精确匹配 ID 或名称。
        # ID 不主动展示，但仍允许高级玩家输入。
        for target in targets:
            if value == target.id or value == target.name:
                return target.id

        # 3. 名称 / 关键词模糊匹配。
        matched_targets = []
        normalized_value = value.lower()

        for target in targets:
            target_name = target.name.lower()
            target_keywords = [
                keyword.lower()
                for keyword in target.search_keywords
            ]

            if normalized_value in target_name:
                matched_targets.append(target)
                continue

            if any(normalized_value in keyword for keyword in target_keywords):
                matched_targets.append(target)

        if len(matched_targets) == 1:
            return matched_targets[0].id

        if len(matched_targets) > 1:
            print("匹配到多个调查对象，请输入上方编号：")

            for target in matched_targets:
                index = targets.index(target) + 1
                target_type = self._format_enum_value(target.type)
                print(f"{index}. {target.name}（{target_type}）")

            return None

        print(f"未找到匹配的调查对象：{value}")
        return None

    def _format_enum_value(self, value) -> str:
        """
        格式化枚举值。

        InvestigationTarget.type 是 Enum。
        这里统一转换成字符串，避免 CLI 直接打印 InvestigationTargetType.BODY。
        """

        return str(getattr(value, "value", value))

    def show_investigation_result(self, result) -> None:
        """
        展示 InvestigationResult。

        展示原则：
        - 新发现线索：展示标题、ID、内容。
        - 已发现过线索：展示标题和 ID，避免重复刷内容。
        - HIDDEN 跳过信息：不展示隐藏线索 ID 和内容。
        """

        print("\n【调查结果】")
        print(f"调查对象：{result.target_name}（{result.target_type}）")
        print(f"描述：{result.target_description}")
        print(result.message)

        if result.newly_discovered_clues:
            print("\n【新发现线索】")
            for clue in result.newly_discovered_clues:
                print(f"- {clue.title}")
                print(f"  ID：{clue.id}")
                print(f"  内容：{clue.content}")

        if result.already_discovered_clues:
            print("\n【已发现过的线索】")
            for clue in result.already_discovered_clues:
                print(f"- {clue.title}")
                print(f"  ID：{clue.id}")

        if result.skipped_hidden_clue_ids:
            print("\n提示：有些信息暂时无法通过普通调查确认。")
