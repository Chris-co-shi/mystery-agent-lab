from stery.application.game_runtime import GameRuntime
from stery.case.case_notebook_service import CaseNotebookService
from stery.case.known_info_search_service import KnownInfoSearchService
from stery.clue import ClueSearchService
from stery.investigation.investigation_service import InvestigationService, InvestigationTargetNotFoundError
from stery.npc.npc_interaction_service import NPCInteractionService
from stery.judge.rule_judge import RuleJudge
from stery.application.session_recorder import SessionRecorder
from stery.case.case_recorder import CaseRecorder


def _format_character_display_name(
        character_id: str,
        characters_by_id: dict,
) -> str:
    character = characters_by_id.get(character_id)

    if character is None:
        return character_id

    return f"{character.name}（{character.id}）"


def _normalize_action_type(record) -> str:
    """
    将 CaseRecord.action_type 统一转成大写字符串。

    为什么要单独做这个小函数：
    - action_type 可能是 Enum，也可能是普通字符串。
    - CLI 只负责展示，不应该依赖具体枚举实现细节。
    - 这里做兼容处理，避免后续 CaseActionType 调整时 CLI 直接报错。
    """

    value = getattr(record, "action_type", None)
    value = getattr(value, "value", value)

    if value is None:
        return ""

    return str(value).upper()


def _get_record_metadata(record) -> dict:
    """
    安全读取 CaseRecord.metadata。

    说明：
    - 旧数据或测试桩里 metadata 可能为空。
    - CLI 展示层不能因为 metadata 缺失导致整个命令失败。
    """

    metadata = getattr(record, "metadata", None)

    if isinstance(metadata, dict):
        return metadata

    return {}


def _is_search_case_record_match(match) -> bool:
    """
    判断 KnownInfoSearchService 返回项是否是“搜索行为记录”。

    /search 的职责是检索“玩家已经知道的信息”，而不是把玩家刚刚执行过的
    搜索动作也当作知识返回。否则会出现：
        搜索“终端” -> 结果里出现“玩家搜索了：终端”

    这里在 CLI 层做一道展示过滤，保证即使底层 service 暂时把 SEARCH
    case record 纳入检索源，也不会污染玩家看到的检索结果。
    更彻底的做法是后续在 KnownInfoSearchService 内部过滤 SEARCH 记录。
    """

    source_type = str(getattr(match, "source_type", "")).upper()
    title = str(getattr(match, "title", "")).strip()
    content = str(getattr(match, "content", "")).strip()

    if source_type != "CASE_RECORD":
        return False

    return (
            title.startswith("搜索：")
            or title.startswith("[搜索]")
            or content.startswith("玩家搜索了：")
    )


def _visible_known_info_matches(result) -> list:
    """
    返回玩家真正应该看到的 /search 命中项。

    当前只过滤 SEARCH 行为记录。
    其他 CaseRecord，例如 INVESTIGATE / ASK_NPC，是否展示由业务阶段决定。
    """

    return [
        match
        for match in getattr(result, "matches", [])
        if not _is_search_case_record_match(match)
    ]


def _format_clue_reference(clue_id: str, clues_by_id: dict | None = None) -> str:
    """
    将 clue_id 格式化成适合玩家阅读的文本。

    优先展示线索标题，同时保留 ID 方便开发调试和最终提交排查。
    如果当前线索未出现在玩家已发现线索里，则只展示 ID，避免误泄露内容。
    """

    if not clues_by_id:
        return clue_id

    clue = clues_by_id.get(clue_id)

    if clue is None:
        return clue_id

    title = getattr(clue, "title", clue_id)
    return f"{title}（{clue_id}）"


def _show_clue_id_list(
        *,
        label: str,
        clue_ids: list[str],
        clues_by_id: dict | None = None,
) -> None:
    """
    统一展示线索 ID 列表。

    用于 /review 的调查记录详情：
    - 新发现线索
    - 已知线索
    """

    if not clue_ids:
        return

    print(f"   {label}：")
    for clue_id in clue_ids:
        print(f"   - {_format_clue_reference(clue_id, clues_by_id)}")


def show_known_info_search_result(result) -> None:
    """
    展示已知信息检索结果。

    V0.2.0 语义：
    - /search 只检索“已知信息”。
    - /search 不解锁新线索。
    - /search 不应该把 SEARCH 行为记录本身展示成结果。
    """

    visible_matches = _visible_known_info_matches(result)

    print("\n【检索结果】")
    print(f"关键词：{result.keyword}")

    if not visible_matches:
        print("在已知信息中没有找到匹配结果。")
        return

    print(f"在已知信息中找到 {len(visible_matches)} 条匹配结果。")

    for index, match in enumerate(visible_matches, start=1):
        print()
        print(f"{index}. [{match.source_type}] {match.title}")

        if match.source_id:
            print(f"   来源 ID：{match.source_id}")

        if match.content:
            print(f"   内容：{match.content}")


def show_clue_search_result(result) -> None:
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


def _show_case_evidence_candidates(clues) -> None:
    """
    展示可作为最终提交参考的证据候选。

    当前 MVP 只根据 clue.is_key_clue 判断。
    不做自动推理，不判断证据是否足够。
    """

    print("\n【证据候选】")

    if not clues:
        print("暂无证据候选。")
        return

    for index, clue in enumerate(clues, start=1):
        print(f"{index}. {clue.title}")
        print(f"   ID：{clue.clue_id}")


def _show_case_npc_questions(questions) -> None:
    """
    展示 NPC 问答摘要。
    """

    print("\n【NPC 问答】")

    if not questions:
        print("暂无 NPC 问答记录。")
        return

    for index, item in enumerate(questions, start=1):
        print(f"{index}. {item.target_character_name}（{item.target_character_id}）")
        print(f"   问：{item.question}")

        if item.answer:
            print(f"   答：{item.answer}")
        else:
            print("   答：<暂无回答记录>")


def _show_case_investigated_targets(
        targets,
        clues_by_id: dict | None = None,
) -> None:
    """
    展示已调查对象。

    /case 是“案件笔记本”，不是单纯动作流水。
    因此这里尽量把调查对象和已发现线索关联起来展示，帮助玩家复盘。
    """

    print("\n【已调查对象】")

    if not targets:
        print("暂无已调查对象。")
        return

    for index, target in enumerate(targets, start=1):
        print(f"{index}. {target.target_name}（{target.target_type}）")
        print(f"   ID：{target.target_id}")

        _show_clue_id_list(
            label="新发现线索",
            clue_ids=list(target.newly_discovered_clue_ids),
            clues_by_id=clues_by_id,
        )

        _show_clue_id_list(
            label="已知线索",
            clue_ids=list(target.already_discovered_clue_ids),
            clues_by_id=clues_by_id,
        )


def _show_case_discovered_clues(clues) -> None:
    """
    展示已发现线索。
    """

    print("\n【已发现线索】")

    if not clues:
        print("暂无已发现线索。")
        return

    for index, clue in enumerate(clues, start=1):
        print(f"{index}. {clue.title}")
        print(f"   ID：{clue.clue_id}")
        print(f"   内容：{clue.content}")

        if clue.reasoning_tags:
            print(f"   标签：{'、'.join(clue.reasoning_tags)}")


def _resolve_character_id(*, raw: str, candidates) -> str | None:
    """
    将玩家输入解析成 character_id。

    支持：
    1. 编号
    2. 精确 ID
    3. 精确姓名
    4. 姓名模糊匹配

    匹配多个时不自动猜，提示玩家重新输入。
    """

    value = raw.strip()

    if value.isdigit():
        index = int(value)

        if 1 <= index <= len(candidates):
            return candidates[index - 1].id

        print(f"无效编号：{value}。请输入 1 到 {len(candidates)} 之间的数字。")
        return None

    for character in candidates:
        if value == character.id or value == character.name:
            return character.id

    matched = [
        character
        for character in candidates
        if value in character.name
    ]

    if len(matched) == 1:
        return matched[0].id

    if len(matched) > 1:
        print("匹配到多个人物，请输入编号或完整姓名：")
        for character in matched:
            index = candidates.index(character) + 1
            print(f"{index}. {character.name}（{character.id}）")
        return None

    print(f"未找到匹配的人物：{value}")
    return None


def _resolve_single_clue_id(*, token: str, candidates) -> str | None:
    """
    解析单个证据输入项。
    """

    value = token.strip()

    if value.isdigit():
        index = int(value)

        if 1 <= index <= len(candidates):
            return candidates[index - 1].clue_id

        print(f"无效证据编号：{value}。请输入 1 到 {len(candidates)} 之间的数字。")
        return None

    for clue in candidates:
        if value == clue.clue_id or value == clue.title:
            return clue.clue_id

    matched = [
        clue
        for clue in candidates
        if value in clue.title
    ]

    if len(matched) == 1:
        return matched[0].clue_id

    if len(matched) > 1:
        print(f"证据输入「{value}」匹配到多个线索，请输入编号或完整标题：")
        for clue in matched:
            index = candidates.index(clue) + 1
            print(f"{index}. {clue.title}（{clue.clue_id}）")
        return None

    # 保留开发调试兼容：
    # 如果玩家输入的是不在 candidates 中的 clue_id，仍然允许提交。
    # Runtime / RuleJudge 后续会校验 clue_id 是否存在。
    if value.startswith("clue_"):
        return value

    print(f"未找到匹配的证据：{value}")
    return None


def _resolve_clue_ids(*, raw: str, candidates) -> list[str] | None:
    """
    将玩家输入解析成 clue_id 列表。

    支持：
    - 编号
    - clue_id
    - clue title
    - title 模糊匹配

    注意：
    - 去重但保留玩家输入顺序。
    - 某一项解析失败时，整体返回 None，避免误提交。
    """

    selected_ids: list[str] = []
    seen: set[str] = set()

    tokens = [
        item.strip()
        for item in raw.split(",")
        if item.strip()
    ]

    if not tokens:
        return []

    for token in tokens:
        clue_id = _resolve_single_clue_id(
            token=token,
            candidates=candidates,
        )

        if clue_id is None:
            return None

        if clue_id in seen:
            continue

        seen.add(clue_id)
        selected_ids.append(clue_id)

    return selected_ids


def _prompt_key_evidence_ids(notebook) -> list[str] | None:
    """
    让玩家选择关键证据。

    证据候选优先来自 notebook.evidence_candidates。
    如果没有 evidence_candidates，则 fallback 到 discovered_clues。

    V0.2.0 交互修正：
    - 输入错误时不直接退出 /submit，而是停留在关键证据选择环节。
    - 只有玩家明确输入 q / quit / exit / 取消 / 退出 时，才取消本次提交。
    - 直接回车表示不提交关键证据，继续进入评分流程。

    返回：
        list[str]：线索 ID 列表。
        None：玩家主动取消本次提交。
    """

    candidates = list(notebook.evidence_candidates)

    if not candidates:
        candidates = list(notebook.discovered_clues)

    print("\n【关键证据候选】")

    if not candidates:
        print("当前没有已发现线索可作为证据。")
        print("你仍可以直接输入 clue_id，多个用英文逗号分隔。")
        print("直接回车表示不提交关键证据；输入 q / 取消 可取消本次提交。")

        while True:
            raw = input("关键证据：").strip()

            if raw.lower() in {"q", "quit", "exit"} or raw in {"取消", "退出"}:
                print("已取消本次提交。")
                return None

            if not raw:
                return []

            selected_ids = [
                item.strip()
                for item in raw.split(",")
                if item.strip()
            ]

            invalid_items = [
                item
                for item in selected_ids
                if not item.startswith("clue_")
            ]

            if invalid_items:
                print(
                    "未找到匹配的证据："
                    f"{'、'.join(invalid_items)}"
                )
                print("请输入 clue_id，或直接回车不提交关键证据；输入 q 可取消本次提交。")
                continue

            return selected_ids

    for index, clue in enumerate(candidates, start=1):
        print(f"{index}. {clue.title}")
        print(f"   ID：{clue.clue_id}")

        if clue.reasoning_tags:
            print(f"   标签：{'、'.join(clue.reasoning_tags)}")

    print("\n请输入关键证据编号、标题或 ID，多个用英文逗号分隔。")
    print("直接回车表示不提交关键证据；输入 q / 取消 可取消本次提交。")

    while True:
        raw = input("关键证据：").strip()

        if raw.lower() in {"q", "quit", "exit"} or raw in {"取消", "退出"}:
            print("已取消本次提交。")
            return None

        if not raw:
            return []

        selected_ids = _resolve_clue_ids(
            raw=raw,
            candidates=candidates,
        )

        if selected_ids is not None:
            return selected_ids

        print("请重新输入关键证据编号、标题或 ID；输入 q 可取消本次提交。")


def _part_get(part, key: str, default=None):
    """
    兼容读取 dict / object 两种评分项结构。
    """

    if part is None:
        return default

    if isinstance(part, dict):
        return part.get(key, default)

    return getattr(part, key, default)


def _build_clue_title_by_id(script) -> dict[str, str]:
    """
    构建 clue_id -> clue title 映射。

    评分模块内部继续用 clue_id 做稳定匹配。
    CLI 是玩家展示层，因此在这里把 clue_id 转成玩家可读的线索标题。
    """

    result: dict[str, str] = {}

    for clue in getattr(script, "clues", []) or []:
        clue_id = getattr(clue, "id", None) or getattr(clue, "clue_id", None)
        title = getattr(clue, "title", None)

        if clue_id and title:
            result[str(clue_id)] = str(title)

    return result


def _format_clue_id_for_score(
        clue_id: str,
        clue_title_by_id: dict[str, str],
) -> str:
    """
    将评分结果中的 clue_id 转成线索标题。
    """

    return clue_title_by_id.get(str(clue_id), str(clue_id))


def _format_clue_ids_for_score(
        clue_ids: list[str] | tuple[str, ...] | None,
        clue_title_by_id: dict[str, str],
) -> list[str]:
    """
    批量格式化评分结果中的 clue_id。
    """

    if not clue_ids:
        return []

    return [
        _format_clue_id_for_score(str(clue_id), clue_title_by_id)
        for clue_id in clue_ids
        if str(clue_id).strip()
    ]


def _print_name_list(label: str, items: list[str]) -> None:
    """
    打印玩家可读的名称列表。
    """

    print(f"  {label}：")

    if not items:
        print("  - 无")
        return

    for item in items:
        print(f"  - {item}")


def _print_score_part(label: str, part) -> None:
    """
    打印通用评分项。
    """

    if not part:
        return

    score = _part_get(part, "score", 0)
    max_score = _part_get(part, "max_score", 0)
    reason = _part_get(part, "reason", "")

    print(f"- {label}：{score}/{max_score}")

    if reason:
        print(f"  {reason}")


def _print_key_evidence_score_part(
        part,
        clue_title_by_id: dict[str, str],
) -> None:
    """
    打印关键证据评分项。

    内部保留 clue_id，玩家界面展示线索标题。
    """

    if not part:
        return

    score = _part_get(part, "score", 0)
    max_score = _part_get(part, "max_score", 0)
    reason = _part_get(part, "reason", "")

    matched_ids = (
            _part_get(part, "matched_ids", None)
            or _part_get(part, "matched_clue_ids", [])
            or []
    )
    missing_ids = (
            _part_get(part, "missing_ids", None)
            or _part_get(part, "missing_clue_ids", [])
            or []
    )

    matched_titles = _format_clue_ids_for_score(matched_ids, clue_title_by_id)
    missing_titles = _format_clue_ids_for_score(missing_ids, clue_title_by_id)

    print(f"- 关键证据：{score}/{max_score}")

    if reason:
        print(f"  {reason}")

    _print_name_list("命中", matched_titles)
    _print_name_list("缺失", missing_titles)


def _print_keyword_score_part(label: str, part) -> None:
    """
    打印关键词型评分项。
    """

    if not part:
        return

    score = _part_get(part, "score", 0)
    max_score = _part_get(part, "max_score", 0)
    reason = _part_get(part, "reason", "")
    matched_keywords = _part_get(part, "matched_keywords", []) or []
    missing_keywords = _part_get(part, "missing_keywords", []) or []

    print(f"- {label}：{score}/{max_score}")

    if reason:
        print(f"  {reason}")

    if matched_keywords or missing_keywords:
        print(f"  命中关键词：{'、'.join(matched_keywords) if matched_keywords else '无'}")
        print(f"  缺失关键词：{'、'.join(missing_keywords) if missing_keywords else '无'}")


def _show_score_breakdown(result, script=None) -> None:
    """
    展示 V0.2.0 评分拆解。

    展示层规则：
    - 内部评分结果仍保留 ID。
    - 玩家界面默认把关键证据 ID 转成线索标题。
    """

    breakdown = getattr(result, "score_breakdown", None)

    if not breakdown:
        return

    clue_title_by_id = _build_clue_title_by_id(script)

    print("\n【评分拆解】")

    _print_score_part("凶手", breakdown.get("murderer"))
    _print_key_evidence_score_part(
        breakdown.get("key_evidence"),
        clue_title_by_id,
    )
    _print_keyword_score_part("动机", breakdown.get("motive"))
    _print_keyword_score_part("手法", breakdown.get("method"))


def _show_review_questions(
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

        npc_display_name = _format_character_display_name(
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


def _show_review_asked_npcs(
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
        npc_display_name = _format_character_display_name(
            character_id=character_id,
            characters_by_id=characters_by_id,
        )
        print(f"- {npc_display_name}：{count} 次")


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

    def show_history(self) -> None:
        """
        兼容旧命令：/history。

        V0.2.0 中不再把 history 定义为“问答历史”。
        原因：
        - 玩家理解的 history 通常是完整行动历史。
        - 当前版本已经有 case_records，可以统一承载调查、搜索、问答、提交。
        - 因此 /history 统一转到 /review，避免玩家刚调查完却看到“暂无问答记录”。
        """

        print("\n提示：/history 已并入 /review，下面显示完整调查记录。")
        self.show_review()

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

    def show_askable_npcs(self, candidates=None) -> None:
        """
        展示当前可询问 NPC。

        为什么不能复用 show_characters()：
        - characters 是玩家可见人物全集，可能包含死者、背景角色、不可对话角色。
        - /ask 最终会调用 NPCInteractionService，它要求目标角色必须存在 npc_profile。
        - 如果把死者也列出来，玩家选择死者时会触发
          “NPC profile not found for character_id: xxx”。

        因此 /ask 使用这个更窄的候选列表：
        - 优先取存在 npc_profile 的角色。
        - 排除 is_victim=True 或 role 中包含“死者”的角色。
        - 玩家仍然可以通过编号、姓名、ID 选择，但只能在可询问 NPC 中选择。
        """

        print("\n【可询问 NPC】")

        if candidates is None:
            candidates = self._get_askable_npc_candidates()

        if not candidates:
            print("当前没有可询问 NPC。")
            return

        for index, character in enumerate(candidates, start=1):
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
        询问 NPC。

        V0.2.0 交互优化：
        - 玩家不再必须复制 NPC ID。
        - 支持输入编号、姓名或 ID。
        - NPC 回答会记录到 case_records，后续可在 /review 和 /case 中查看。

        注意：
        - NPC 回答属于“证言”，不等价于事实。
        - NPC 可能说谎、回避、主观怀疑或被玩家诱导。
        - 防泄底、防编造仍然由 NPCInteractionService / Guardrail 负责。
        """

        print("\n【询问 NPC】")

        # /ask 的候选对象必须是“真正可对话的 NPC”，不能直接使用全部 characters。
        # characters 里可能包含死者，例如 victim_shen_weizhou；
        # 但 NPCInteractionService 只接受存在 npc_profile 的角色。
        candidates = self._get_askable_npc_candidates()

        if not candidates:
            print("当前没有可询问 NPC。")
            return

        self.show_askable_npcs(candidates)

        raw_target = input("\n请输入要询问的 NPC 编号、姓名或 ID：").strip()
        question = input("请输入你的问题：").strip()

        if not raw_target or not question:
            print("询问对象和问题不能为空。")
            return

        target_character_id = _resolve_character_id(
            raw=raw_target,
            candidates=candidates,
        )

        if target_character_id is None:
            return

        try:
            state = self.runtime.state
            if state is None:
                print("游戏尚未开始。")
                return

            result = self.npc_interaction_service.ask_npc(
                target_character_id=target_character_id,
                question=question,
            )

            self.case_recorder.record_ask_npc(
                state=state,
                npc_id=result.target_character_id,
                npc_name=self._get_character_name(result.target_character_id),
                question=result.question,
                answer=result.npc_answer,
            )
        except Exception as exc:
            print(f"询问失败：{exc}")
            return

        print("\n【NPC 回答】")
        print(result.npc_answer)

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

        if command == "/history":
            # 理论上 _normalize_command 已经把 /history 转成 /review。
            # 这里保留兜底，方便单元测试直接调用 handle_command("/history")。
            self.show_history()
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

    def _get_askable_npc_candidates(self):
        """
        获取 /ask 可询问 NPC 候选。

        候选来源必须和 NPCInteractionService 的能力对齐：
        - 优先使用 npc_profiles 中存在的 character_id。
        - 排除死者 / 受害者。
        - 如果剧本暂时没有 npc_profiles，则退回到 is_npc=True 的非死者角色。

        这样可以避免 UI 允许玩家选择“沈维舟（死者）”，
        但服务层又因为找不到 npc_profile 而返回兜底回答。
        """

        characters = self.runtime.list_characters()
        profile_character_ids = self._get_npc_profile_character_ids()

        if profile_character_ids:
            return [
                character
                for character in characters
                if character.id in profile_character_ids
                   and not self._is_victim_character(character)
            ]

        return [
            character
            for character in characters
            if getattr(character, "is_npc", False)
               and not self._is_victim_character(character)
        ]

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
