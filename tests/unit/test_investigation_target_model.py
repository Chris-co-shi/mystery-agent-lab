import pytest
from pydantic import ValidationError

from stery.domain import ClueVisibility, GamePhase
from stery.domain.models import GameScript, InvestigationTargetType


def build_minimal_script_payload() -> dict:
    """
    构造一个最小可加载剧本 payload。

    这个测试只关注 investigation_targets 模型扩展，
    不测试 InvestigationService，也不测试 CLI。
    """

    return {
        "id": "test_script",
        "title": "测试剧本",
        "version": "v0.2.0",
        "background": "这是一个用于测试调查对象模型的剧本。",
        "rules": {
            "max_question_rounds": 5,
            "allow_free_question": True,
            "allow_clue_search": True,
            "final_vote": [
                "suspect_character_id",
                "motive",
                "method",
                "key_evidence",
            ],
        },
        "characters": [
            {
                "id": "npc_doctor",
                "name": "周医生",
                "role": "私人医生",
                "is_npc": True,
                "public_profile": "死者的私人医生。",
            }
        ],
        "npc_profiles": [],
        "clues": [
            {
                "id": "clue_wine",
                "title": "红酒杯残留异味",
                "content": "红酒杯中有异常苦味。",
                "visibility": ClueVisibility.PUBLIC,
                "unlock_phase": GamePhase.START,
                "related_character_ids": ["npc_doctor"],
                "is_key_clue": True,
                "search_keywords": ["红酒", "酒杯"],
            },
            {
                "id": "clue_lip",
                "title": "死者嘴唇发紫",
                "content": "死者嘴唇呈现异常紫色。",
                "visibility": ClueVisibility.PUBLIC,
                "unlock_phase": GamePhase.START,
                "related_character_ids": [],
                "is_key_clue": True,
                "search_keywords": ["尸体", "嘴唇"],
            },
        ],
        "truth": {
            "id": "npc_doctor",
            "murderer_id": "npc_doctor",
            "motive": "被死者长期勒索。",
            "method": "将镇静剂混入红酒中。",
            "key_clue_ids": ["clue_wine", "clue_lip"],
            "motive_keywords": ["勒索"],
            "method_keywords": ["镇静剂", "红酒"],
            "summary": "周医生因被勒索而投药杀害死者。",
        },
        "timeline": [],
    }


def test_old_script_without_investigation_targets_can_still_load():
    """
    旧剧本没有 investigation_targets 时仍然可以加载。

    这是 V0.2.0 协议扩展的兼容性要求。
    """

    payload = build_minimal_script_payload()

    script = GameScript.model_validate(payload)

    assert script.investigation_targets == []


def test_script_with_room_body_item_investigation_targets_can_load():
    """
    V0.2.0 新剧本可以声明 ROOM / BODY / ITEM 三类调查对象。
    """

    payload = build_minimal_script_payload()

    payload["investigation_targets"] = [
        {
            "id": "target_study",
            "name": "书房",
            "type": "ROOM",
            "description": "顾明远遇害的房间，地上有摔碎的红酒杯。",
            "search_keywords": ["书房", "现场", "房间"],
            "discoverable_clue_ids": ["clue_wine"],
        },
        {
            "id": "target_body",
            "name": "顾明远的尸体",
            "type": "BODY",
            "description": "死者倒在书房地毯上，嘴唇颜色异常。",
            "search_keywords": ["尸体", "死者", "嘴唇"],
            "discoverable_clue_ids": ["clue_lip"],
        },
        {
            "id": "target_wine_glass",
            "name": "摔碎的红酒杯",
            "type": "ITEM",
            "description": "红酒杯碎片散落在尸体旁。",
            "search_keywords": ["红酒杯", "酒杯", "碎片"],
            "discoverable_clue_ids": ["clue_wine"],
        },
    ]

    script = GameScript.model_validate(payload)

    assert len(script.investigation_targets) == 3

    assert script.investigation_targets[0].type == InvestigationTargetType.ROOM
    assert script.investigation_targets[1].type == InvestigationTargetType.BODY
    assert script.investigation_targets[2].type == InvestigationTargetType.ITEM

    assert script.investigation_targets[0].discoverable_clue_ids == ["clue_wine"]


def test_investigation_target_with_invalid_type_should_fail():
    """
    investigation_targets[].type 只能是 ROOM / BODY / ITEM。
    """

    payload = build_minimal_script_payload()

    payload["investigation_targets"] = [
        {
            "id": "target_unknown",
            "name": "未知目标",
            "type": "PERSON",
            "description": "非法类型。",
            "search_keywords": [],
            "discoverable_clue_ids": [],
        }
    ]

    with pytest.raises(ValidationError):
        GameScript.model_validate(payload)


def test_investigation_target_referencing_unknown_clue_should_fail():
    """
    discoverable_clue_ids 引用不存在的 clue_id 时应该失败。

    这样可以提前发现剧本引用错误，而不是等到 /investigate 执行时才失败。
    """

    payload = build_minimal_script_payload()

    payload["investigation_targets"] = [
        {
            "id": "target_body",
            "name": "顾明远的尸体",
            "type": "BODY",
            "description": "死者倒在书房地毯上。",
            "search_keywords": ["尸体"],
            "discoverable_clue_ids": ["clue_not_exists"],
        }
    ]

    with pytest.raises(ValidationError, match="references unknown clue_id"):
        GameScript.model_validate(payload)


def test_unknown_investigation_target_field_should_fail():
    """
    因为 ScriptBaseModel 使用 extra='forbid'，
    investigation_targets 中出现未定义字段时应该失败。

    这可以防止剧本 JSON 字段写错后被静默忽略。
    """

    payload = build_minimal_script_payload()

    payload["investigation_targets"] = [
        {
            "id": "target_body",
            "name": "顾明远的尸体",
            "type": "BODY",
            "description": "死者倒在书房地毯上。",
            "search_keywords": ["尸体"],
            "discoverable_clue_ids": ["clue_lip"],
            "wrong_field": "不应该存在",
        }
    ]

    with pytest.raises(ValidationError):
        GameScript.model_validate(payload)