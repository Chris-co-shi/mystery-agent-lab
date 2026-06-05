from stery.domain import ClueVisibility, GamePhase
from stery.domain.models import Character, Clue, GameRules, GameScript, Truth
from stery.domain.state import FinalVote
from stery.judge.rule_judge import RuleJudge


def build_script(
    *,
    rules: GameRules | None = None,
    truth: Truth | None = None,
) -> GameScript:
    """
    构造一个最小可判案剧本。

    这个测试只关注 RuleJudge + scoring 接入。
    不测试 NPC、不测试 CLI、不测试线索搜索。
    """

    return GameScript(
        id="test_script",
        title="测试剧本",
        version="v0.2.0",
        background="测试背景。",
        rules=rules
        or GameRules(
            max_question_rounds=5,
            allow_free_question=True,
            allow_clue_search=True,
            final_vote=["suspect_character_id", "motive", "method", "key_evidence"],
        ),
        characters=[
            Character(
                id="npc_doctor",
                name="周医生",
                role="私人医生",
                is_npc=True,
                public_profile="死者的私人医生。",
            ),
            Character(
                id="npc_butler",
                name="林伯",
                role="管家",
                is_npc=True,
                public_profile="顾家的老管家。",
            ),
        ],
        npc_profiles=[],
        clues=[
            Clue(
                id="clue_wine",
                title="红酒杯残留异味",
                content="红酒杯中有异常苦味。",
                visibility=ClueVisibility.PUBLIC,
                unlock_phase=GamePhase.START,
            ),
            Clue(
                id="clue_lip",
                title="死者嘴唇发紫",
                content="死者嘴唇呈现异常紫色。",
                visibility=ClueVisibility.PUBLIC,
                unlock_phase=GamePhase.START,
            ),
            Clue(
                id="clue_drug",
                title="药瓶残留",
                content="药瓶中有镇静剂残留。",
                visibility=ClueVisibility.PUBLIC,
                unlock_phase=GamePhase.START,
            ),
        ],
        truth=truth
        or Truth(
            id="npc_doctor",
            murderer_id="npc_doctor",
            motive="被死者长期勒索",
            method="将镇静剂混入红酒中投药",
            key_clue_ids=["clue_wine", "clue_lip"],
            motive_keywords=["勒索"],
            method_keywords=["镇静剂", "红酒", "投药"],
            summary="周医生因被勒索而投药杀害死者。",
        ),
        timeline=[],
    )


def test_rule_judge_uses_default_scoring():
    """
    没有显式配置 rules.scoring 时，
    应使用默认 40/30/15/15。
    """

    script = build_script()

    vote = FinalVote(
        suspect_character_id="npc_doctor",
        motive="被死者勒索",
        method="镇静剂混入红酒投药",
        key_evidence=["clue_wine", "clue_lip"],
    )

    result = RuleJudge(script).evaluate_final_vote(vote)

    assert result.score == 100
    assert result.max_score == 100
    assert result.is_correct is True

    breakdown = result.score_breakdown

    assert breakdown["murderer"]["score"] == 40
    assert breakdown["key_evidence"]["score"] == 30
    assert breakdown["motive"]["score"] == 15
    assert breakdown["method"]["score"] == 15


def test_rule_judge_wrong_method_gets_zero_method_score():
    """
    回归 V0.1.3 的核心问题：
    玩家写“勒死”，不能命中“镇静剂/红酒/投药”。

    即使凶手、关键线索、动机都正确，手法也必须 0 分。
    """

    script = build_script()

    vote = FinalVote(
        suspect_character_id="npc_doctor",
        motive="被死者勒索",
        method="勒死",
        key_evidence=["clue_wine", "clue_lip"],
    )

    result = RuleJudge(script).evaluate_final_vote(vote)

    assert result.score == 85
    assert result.is_correct is False

    breakdown = result.score_breakdown

    assert breakdown["murderer"]["score"] == 40
    assert breakdown["key_evidence"]["score"] == 30
    assert breakdown["motive"]["score"] == 15
    assert breakdown["method"]["score"] == 0
    assert breakdown["method"]["matched_keywords"] == []
    assert breakdown["method"]["missing_keywords"] == ["镇静剂", "红酒", "投药"]


def test_rule_judge_partial_key_evidence_scores_by_ratio():
    """
    关键证据只命中一部分时，应按比例得分。
    """

    script = build_script(
        truth=Truth(
            id="npc_doctor",
            murderer_id="npc_doctor",
            motive="被死者长期勒索",
            method="将镇静剂混入红酒中投药",
            key_clue_ids=["clue_wine", "clue_lip", "clue_drug"],
            motive_keywords=["勒索"],
            method_keywords=["镇静剂", "红酒", "投药"],
            summary="周医生因被勒索而投药杀害死者。",
        )
    )

    vote = FinalVote(
        suspect_character_id="npc_doctor",
        motive="勒索",
        method="镇静剂混入红酒投药",
        key_evidence=["clue_wine", "clue_drug"],
    )

    result = RuleJudge(script).evaluate_final_vote(vote)

    # 凶手 40 + 证据 20 + 动机 15 + 手法 15 = 90
    assert result.score == 90
    assert result.is_correct is False

    evidence = result.score_breakdown["key_evidence"]

    assert evidence["score"] == 20
    assert evidence["matched_clue_ids"] == ["clue_wine", "clue_drug"]
    assert evidence["missing_clue_ids"] == ["clue_lip"]


def test_rule_judge_fallback_to_truth_id_when_murderer_id_missing():
    """
    兼容旧剧本：
    如果 truth.murderer_id 缺失，则 fallback 到 truth.id。
    """

    script = build_script(
        truth=Truth(
            id="npc_doctor",
            murderer_id=None,
            motive="被死者长期勒索",
            method="将镇静剂混入红酒中投药",
            key_clue_ids=["clue_wine", "clue_lip"],
            motive_keywords=["勒索"],
            method_keywords=["镇静剂", "红酒", "投药"],
            summary="周医生因被勒索而投药杀害死者。",
        )
    )

    vote = FinalVote(
        suspect_character_id="npc_doctor",
        motive="勒索",
        method="镇静剂混入红酒投药",
        key_evidence=["clue_wine", "clue_lip"],
    )

    result = RuleJudge(script).evaluate_final_vote(vote)

    assert result.score == 100
    assert result.is_correct is True