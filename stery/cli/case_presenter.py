"""
CLI case notebook presenter.

这个模块只负责 /case 案件笔记本展示。
不读取 Runtime，不修改 GameState。
"""

from stery.cli.review_presenter import _show_clue_id_list


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


__all__ = [
    "_show_case_discovered_clues",
    "_show_case_evidence_candidates",
    "_show_case_investigated_targets",
    "_show_case_npc_questions",
]