from stery.application.game_runtime import GameRuntime
from stery.case.case_notebook_service import CaseNotebookService
from stery.case.known_info_search_service import KnownInfoSearchService
from stery.cli.ask_flow import  AskFlow
from stery.cli.submit_flow import SubmitFlow
from stery.clue import ClueSearchService
from stery.investigation.investigation_service import InvestigationService
from stery.npc.npc_interaction_service import NPCInteractionService
from stery.judge.rule_judge import RuleJudge
from stery.application.session_recorder import SessionRecorder
from stery.case.case_recorder import CaseRecorder
from stery.cli.commands import normalize_command, show_help
from stery.cli.investigate_flow import InvestigateFlow
from stery.cli.search_flow import SearchFlow
from stery.cli.case_presenter import (
    _show_case_discovered_clues,
    _show_case_evidence_candidates,
    _show_case_investigated_targets,
    _show_case_npc_questions,
)
from stery.cli.review_presenter import (
    _get_record_metadata,
    _normalize_action_type,
    _show_clue_id_list,
)
from stery.cli.selectors import (
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
            command = normalize_command(raw_input)

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

    def investigate_target(self) -> None:
        """
        执行一次调查。

        V0.2.0 交互规则：
        - 玩家先看到可调查对象列表。
        - 玩家可以输入编号、名称、关键词。
        - 如果关键词匹配多个对象，提示候选编号，并继续输入。
        - 不把内部 ID 暴露给普通玩家。
        """

        InvestigateFlow(
            runtime=self.runtime,
            investigation_service=self.investigation_service,
            case_recorder=self.case_recorder,
        ).run()

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

        SearchFlow(
            runtime=self.runtime,
            known_info_search_service=self.known_info_search_service,
            case_recorder=self.case_recorder,
        ).run()

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

        return SubmitFlow(
            runtime=self.runtime,
            rule_judge=self.rule_judge,
            case_notebook_service=self.case_notebook_service,
            case_recorder=self.case_recorder,
            session_recorder=self.session_recorder,
        ).run()

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

