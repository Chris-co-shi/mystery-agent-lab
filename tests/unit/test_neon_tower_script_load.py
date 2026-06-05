import json
from pathlib import Path

from stery.domain.models import GameScript, InvestigationTargetType


SCRIPT_PATH = Path("scripts/neon_tower_silent_chamber.json")


def test_neon_tower_silent_chamber_can_load_as_gamescript():
    """
    验证 neon_tower_silent_chamber 可以被当前 V0.2.0 GameScript 模型加载。

    这个测试只验证协议加载和引用一致性，不测试 InvestigationService。
    """

    payload = json.loads(SCRIPT_PATH.read_text(encoding="utf-8"))

    script = GameScript.model_validate(payload)

    assert script.id == "neon_tower_silent_chamber_001"
    assert script.title == "霓虹塔静默舱"
    assert script.genre == "赛博朋克"
    assert script.difficulty == "MEDIUM_HARD"
    assert script.estimated_minutes == 60

    assert script.truth.murderer_id == "npc_qi_manshu"

    # key_evidence_ids 会通过 AliasChoices 进入内部字段 key_clue_ids。
    assert script.truth.key_clue_ids == [
        "clue_neck_injection_mark",
        "clue_injector_batch_mismatch",
        "clue_preparation_tray_residue",
        "clue_sedative_missing_record",
        "clue_qi_access_preparation",
        "clue_ethics_transfer_file",
    ]

    assert script.truth.motive_keywords
    assert script.truth.method_keywords
    assert script.truth.summary

    assert len(script.investigation_targets) == 9

    target_types = {target.type for target in script.investigation_targets}

    assert InvestigationTargetType.ROOM in target_types
    assert InvestigationTargetType.BODY in target_types
    assert InvestigationTargetType.ITEM in target_types


def test_neon_tower_all_investigation_target_clues_exist():
    """
    验证每个 investigation_target.discoverable_clue_ids 都存在于 clues。
    """

    payload = json.loads(SCRIPT_PATH.read_text(encoding="utf-8"))
    script = GameScript.model_validate(payload)

    clue_ids = {clue.id for clue in script.clues}

    for target in script.investigation_targets:
        for clue_id in target.discoverable_clue_ids:
            assert clue_id in clue_ids


def test_neon_tower_truth_refs_are_valid():
    """
    验证 truth 中的关键引用是有效的。
    """

    payload = json.loads(SCRIPT_PATH.read_text(encoding="utf-8"))
    script = GameScript.model_validate(payload)

    character_ids = {character.id for character in script.characters}
    clue_ids = {clue.id for clue in script.clues}

    assert script.truth.murderer_id in character_ids

    for clue_id in script.truth.key_clue_ids:
        assert clue_id in clue_ids