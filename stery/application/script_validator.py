from stery.domain.models import GameScript


def _validate_npc_profiles(script, character_ids: set[str]) -> None:
    for profile in script.npc_profiles:
        if profile.id not in character_ids:
            raise ValueError(f"NPC Profile {profile.id} 的 id 不在 Character 中")


def _validate_clues(script: GameScript, character_ids: set[str]) -> None:
    for clue in script.clues:
        for character_id in clue.related_character_ids:
            if character_id not in character_ids:
                raise ValueError(
                    f"Clue {clue.id} references unknown character_id: {character_id}"
                )


def _validate_truth(script, character_ids: set[str], clue_ids: set[str]) -> None:
    """
    校验 truth 中的核心引用。

    V0.2.0 兼容策略：
    - 新剧本优先使用 truth.murderer_id 表示真凶。
    - 旧剧本可能仍然用 truth.id 表示真凶。
    - 因此 validator 必须使用 murderer_id or id，而不是只读 truth.id。

    注意：
    - truth.key_clue_ids 是代码内部 canonical 字段。
    - 新生成剧本如果使用 key_evidence_ids，已经在 Truth 模型层通过 alias
      进入 key_clue_ids。
    """

    murderer_id = script.truth.murderer_id or script.truth.id

    if not murderer_id:
        raise ValueError(
            "Truth must define murderer_id. "
            "V0.2.0 scripts should use truth.murderer_id; "
            "V0.1.x compatibility may fallback to truth.id."
        )

    if murderer_id not in character_ids:
        raise ValueError(
            f"Truth references unknown murderer_id: {murderer_id}"
        )

    for clue_id in script.truth.key_clue_ids:
        if clue_id not in clue_ids:
            raise ValueError(
                f"Truth references unknown key clue_id: {clue_id}"
            )


def _validate_timeline(script: GameScript, character_ids: set[str]) -> None:
    for event in script.timeline:
        if event.id not in character_ids:
            raise ValueError(
                f"Timeline event references unknown character_id: {event.id}"
            )

def _validate_investigation_targets(script, clue_ids: set[str]) -> None:
    """
    校验 investigation_targets 引用的 clue_id 是否存在。
    """

    for target in script.investigation_targets:
        for clue_id in target.discoverable_clue_ids:
            if clue_id not in clue_ids:
                raise ValueError(
                    f"InvestigationTarget {target.id} references unknown clue_id: {clue_id}"
                )
def validate_script_references(script: GameScript) -> None:
    character_ids = {character.id for character in script.characters}
    clue_ids = {clue.id for clue in script.clues}

    _validate_npc_profiles(script, character_ids)
    _validate_clues(script, character_ids)
    _validate_truth(script, character_ids, clue_ids)
    _validate_investigation_targets(script, clue_ids)
