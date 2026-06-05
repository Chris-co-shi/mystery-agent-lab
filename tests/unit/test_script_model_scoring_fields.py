import pytest
from pydantic import ValidationError

from stery.domain import ClueVisibility, GamePhase
from stery.domain.models import GameScript


def build_minimal_payload() -> dict:
    """
    构造一个最小可加载剧本 payload。

    这个测试只验证模型字段兼容性：
    - 旧剧本没有 rules.scoring 是否能加载
    - 新剧本有 rules.scoring 是否能加载
    - 新 truth 字段是否能加载
    """

    return {
        "id": "test_script",
        "title": "测试剧本",
        "version": "v0.2.0",
        "background": "这是一个测试剧本。",
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
                "related_character_ids": [],
                "is_key_clue": True,
                "search_keywords": ["红酒"],
            }
        ],
        "truth": {
            "id": "npc_doctor",
            "motive": "被死者长期勒索",
            "method": "将镇静剂混入红酒中投药",
            "key_clue_ids": ["clue_wine"],
            "summary": "周医生因被勒索而杀害死者。",
        },
        "timeline": [],
    }


def test_old_script_without_scoring_and_keywords_can_still_load():
    """
    旧剧本没有 rules.scoring、murderer_id、
    motive_keywords、method_keywords 时，仍然应该能加载。

    这是为了保证 V0.1.x 剧本兼容。
    """

    script = GameScript.model_validate(build_minimal_payload())

    assert script.rules.scoring.murderer_score == 40
    assert script.rules.scoring.key_evidence_score == 30
    assert script.rules.scoring.motive_score == 15
    assert script.rules.scoring.method_score == 15

    assert script.truth.murderer_id is None
    assert script.truth.motive_keywords == []
    assert script.truth.method_keywords == []


def test_new_script_with_scoring_and_truth_keywords_can_load():
    """
    V0.2.0 新剧本可以显式声明：
    - rules.scoring
    - truth.murderer_id
    - truth.motive_keywords
    - truth.method_keywords
    """

    payload = build_minimal_payload()

    payload["rules"]["scoring"] = {
        "murderer_score": 50,
        "key_evidence_score": 20,
        "motive_score": 10,
        "method_score": 20,
    }

    payload["truth"]["murderer_id"] = "npc_doctor"
    payload["truth"]["motive_keywords"] = ["勒索"]
    payload["truth"]["method_keywords"] = ["镇静剂", "红酒", "投药"]

    script = GameScript.model_validate(payload)

    assert script.rules.scoring.murderer_score == 50
    assert script.rules.scoring.key_evidence_score == 20
    assert script.rules.scoring.motive_score == 10
    assert script.rules.scoring.method_score == 20

    assert script.truth.murderer_id == "npc_doctor"
    assert script.truth.motive_keywords == ["勒索"]
    assert script.truth.method_keywords == ["镇静剂", "红酒", "投药"]


def test_unknown_scoring_field_should_fail_because_extra_is_forbidden():
    """
    因为 ScriptBaseModel 使用 extra='forbid'，
    如果 rules.scoring 中出现错误字段，应该直接失败。

    这可以防止剧本 JSON 字段写错后被静默忽略。
    """

    payload = build_minimal_payload()

    payload["rules"]["scoring"] = {
        "murderer_score": 40,
        "key_evidence_score": 30,
        "motive_score": 15,
        "method_score": 15,
        "wrong_score": 999,
    }

    with pytest.raises(ValidationError):
        GameScript.model_validate(payload)