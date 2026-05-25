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


def _validate_truth(
        script: GameScript,
        character_ids: set[str],
        clue_ids: set[str],
) -> None:
    if script.truth.id not in character_ids:
        raise ValueError(
            f"Truth references unknown murderer_character_id: "
            f"{script.truth.id}"
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


def validate_script_references(script: GameScript) -> None:
    """
    校验剧本内部 ID 引用关系。

    Pydantic 只负责字段类型校验；
    本函数负责跨对象引用校验。
    """
    character_ids = {character.id for character in script.characters}

    clue_ids = {clue.id for clue in script.clues}

    _validate_npc_profiles(script, character_ids)
    _validate_clues(script, character_ids)
    _validate_truth(script, character_ids, clue_ids)
    _validate_timeline(script, character_ids)
