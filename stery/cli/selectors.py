"""
CLI input selectors.

这个模块只负责把玩家输入解析成内部 ID。

设计边界：
- 不调用业务 service。
- 不修改 GameState。
- 不做展示型业务逻辑。
- 只处理编号 / 名称 / ID / 模糊匹配。
"""


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

    支持：
    - 编号
    - clue_id
    - 线索标题
    - 线索标题模糊匹配

    注意：
    - candidates 来自 notebook.evidence_candidates 或 notebook.discovered_clues。
    - notebook 里的线索字段通常是 clue_id，而不是 id。
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
    # 如果玩家输入的是 clue_xxx 形式，但不在当前候选里，仍允许返回。
    # 后续 RuleJudge / Runtime 会校验 clue_id 是否存在。
    if value.startswith("clue_"):
        return value

    print(f"未找到匹配的证据：{value}")
    return None


def _resolve_clue_ids(*, raw: str, candidates) -> list[str] | None:
    """
    将玩家输入解析成 clue_id 列表。

    支持：
    - 编号：1,2,3
    - clue_id：clue_xxx
    - 线索标题
    - 标题模糊匹配

    返回：
    - list[str]：解析成功
    - None：某一项解析失败
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

    V0.2.2 行为：
    - 输入错误时不直接退出 /submit，而是停留在证据输入环节。
    - 输入 q / quit / exit / 取消 / 退出 时，取消本次提交。
    - 直接回车表示不提交关键证据，继续进入评分。

    返回：
    - list[str]：玩家选择的关键证据 ID。
    - None：玩家主动取消本次提交。
    """

    candidates = list(notebook.evidence_candidates)

    if not candidates:
        candidates = list(notebook.discovered_clues)

    while True:
        print("\n【关键证据候选】")

        if not candidates:
            print("当前没有已发现线索可作为证据。")
            print("你仍可以直接输入 clue_id，多个用英文逗号分隔。")
        else:
            for index, clue in enumerate(candidates, start=1):
                print(f"{index}. {clue.title}")
                print(f"   ID：{clue.clue_id}")

                if clue.reasoning_tags:
                    print(f"   标签：{'、'.join(clue.reasoning_tags)}")

            print("\n请输入关键证据编号、标题或 ID，多个用英文逗号分隔。")

        raw = input("关键证据：").strip()

        if raw.lower() in {"q", "quit", "exit"} or raw in {"取消", "退出", "返回"}:
            print("已取消本次提交。")
            return None

        if not raw:
            return []

        if not candidates:
            return [
                item.strip()
                for item in raw.split(",")
                if item.strip()
            ]

        resolved_ids = _resolve_clue_ids(
            raw=raw,
            candidates=candidates,
        )

        if resolved_ids is not None:
            return resolved_ids

        print("请重新输入关键证据编号、标题或 ID；输入 q 可取消本次提交。")


__all__ = [
    "_prompt_key_evidence_ids",
    "_resolve_character_id",
    "_resolve_clue_ids",
    "_resolve_single_clue_id",
]