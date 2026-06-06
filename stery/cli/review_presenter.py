"""
CLI review presenter helpers.

这个模块负责 /review 相关的展示辅助函数。
暂时不移动 Application._show_review_record_details()，
因为它依赖 self.runtime 和 self._get_character_name，后续第二刀再拆。
"""


def _format_character_display_name(
        character_id: str,
        characters_by_id: dict,
) -> str:
    """
    将 character_id 展示为：姓名（ID）。

    如果找不到角色，则回退显示原始 ID。
    """

    character = characters_by_id.get(character_id)

    if character is None:
        return character_id

    return f"{character.name}（{character.id}）"


def _normalize_action_type(record) -> str:
    """
    将 CaseRecord.action_type 统一转成大写字符串。

    action_type 可能是：
    - Enum
    - 普通字符串
    - None

    CLI 展示层不应该依赖具体枚举实现细节。
    """

    value = getattr(record, "action_type", None)
    value = getattr(value, "value", value)

    if value is None:
        return ""

    return str(value).upper()


def _get_record_metadata(record) -> dict:
    """
    安全读取 CaseRecord.metadata。

    旧数据或测试桩里 metadata 可能为空。
    """

    metadata = getattr(record, "metadata", None)

    if isinstance(metadata, dict):
        return metadata

    return {}


def _format_clue_reference(clue_id: str, clues_by_id: dict | None = None) -> str:
    """
    将 clue_id 格式化成适合玩家阅读的文本。

    优先展示线索标题，同时保留 ID，便于调试和核对。
    如果当前线索未出现在玩家已发现线索中，则只展示 ID，避免误泄露内容。
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

    用于：
    - /review 的调查记录详情
    - /case 的已调查对象关联线索
    """

    if not clue_ids:
        return

    print(f"   {label}：")
    for clue_id in clue_ids:
        print(f"   - {_format_clue_reference(clue_id, clues_by_id)}")


__all__ = [
    "_format_character_display_name",
    "_format_clue_reference",
    "_get_record_metadata",
    "_normalize_action_type",
    "_show_clue_id_list",
]