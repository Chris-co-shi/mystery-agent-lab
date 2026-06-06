"""
Common CLI presenters.

这个模块放通用展示逻辑：
- /search 结果展示
- 旧 clue search 展示
- /submit 评分拆解展示
"""


def _is_search_case_record_match(match) -> bool:
    """
    判断 KnownInfoSearchService 返回项是否是“搜索行为记录”。

    /search 的职责是检索玩家已经知道的信息，
    不是把玩家刚刚执行过的搜索动作也当作知识返回。
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
    """

    return [
        match
        for match in getattr(result, "matches", [])
        if not _is_search_case_record_match(match)
    ]


def show_known_info_search_result(result) -> None:
    """
    展示已知信息检索结果。

    V0.2.0+ 语义：
    - /search 只检索已知信息。
    - /search 不解锁新线索。
    - /search 不展示 SEARCH 行为记录本身。
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
    """
    展示旧版 clue search 结果。

    当前 /search 已经降级为 KnownInfoSearchService。
    这个函数保留是为了兼容旧调用或测试。
    """

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


def _part_get(part, key: str, default=None):
    """
    兼容 dict 和对象两种 score part 结构。
    """

    if part is None:
        return default

    if isinstance(part, dict):
        return part.get(key, default)

    return getattr(part, key, default)


def _build_clue_title_by_id(script) -> dict[str, str]:
    """
    构建 clue_id -> clue title 映射。

    CLI 展示层负责把内部 clue_id 翻译成玩家能看懂的线索标题。
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
    将评分结果里的 clue_id 转成玩家可读标题。
    """

    return clue_title_by_id.get(clue_id, clue_id)


def _format_clue_ids_for_score(
        clue_ids: list[str] | tuple[str, ...] | None,
        clue_title_by_id: dict[str, str],
) -> list[str]:
    """
    批量转换评分结果中的 clue_id。
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
    打印列表型内容。
    """

    print(f"  {label}：")

    if not items:
        print("  - 无")
        return

    for item in items:
        print(f"  - {item}")


def _print_score_part(label: str, part) -> None:
    """
    打印普通评分项。

    用于：
    - 凶手
    - 兼容旧结构
    """

    if not part:
        return

    score = _part_get(part, "score", 0)
    max_score = _part_get(part, "max_score", 0)
    reason = _part_get(part, "reason", "")

    print(f"- {label}：{score}/{max_score}")

    if reason:
        print(f"  {reason}")


def _print_keyword_score_part(label: str, part) -> None:
    """
    打印关键词型评分项。

    用于：
    - 动机
    - 手法
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

    if not matched_keywords and not missing_keywords:
        return

    matched_text = "、".join(matched_keywords) if matched_keywords else "无"
    missing_text = "、".join(missing_keywords) if missing_keywords else "无"

    print(f"  命中关键词：{matched_text}")
    print(f"  缺失关键词：{missing_text}")


def _print_key_evidence_score_part(
        part,
        clue_title_by_id: dict[str, str],
) -> None:
    """
    打印关键证据评分项。

    内部评分使用 clue_id；
    CLI 展示使用 clue title。
    """

    if not part:
        return

    score = _part_get(part, "score", 0)
    max_score = _part_get(part, "max_score", 0)
    reason = _part_get(part, "reason", "")

    matched_ids = _part_get(part, "matched_ids", None)
    missing_ids = _part_get(part, "missing_ids", None)

    # 兼容旧字段名。
    if matched_ids is None:
        matched_ids = _part_get(part, "matched_clue_ids", []) or []

    if missing_ids is None:
        missing_ids = _part_get(part, "missing_clue_ids", []) or []

    matched_titles = _format_clue_ids_for_score(
        matched_ids,
        clue_title_by_id,
    )
    missing_titles = _format_clue_ids_for_score(
        missing_ids,
        clue_title_by_id,
    )

    print(f"- 关键证据：{score}/{max_score}")

    if reason:
        print(f"  {reason}")

    if matched_ids or missing_ids:
        _print_name_list("命中", matched_titles)
        _print_name_list("缺失", missing_titles)


def _show_score_breakdown(result, script=None) -> None:
    """
    展示 V0.2.0+ 评分拆解。

    新规则：
    - Judge / scoring 输出结构化 ID。
    - CLI 根据 script.clues 把 clue_id 转成 clue.title。
    - 玩家界面默认不展示一长串 clue_id。
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


__all__ = [
    "_build_clue_title_by_id",
    "_format_clue_ids_for_score",
    "_show_score_breakdown",
    "show_clue_search_result",
    "show_known_info_search_result"
]