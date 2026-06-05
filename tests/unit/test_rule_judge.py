from __future__ import annotations

import pytest

from stery.domain import ClueVisibility, GamePhase
from stery.domain.models import Character, Clue, GameRules, GameScript, ScoringRule, Truth
from stery.domain.state import FinalVote, GameState
from stery.judge.rule_judge import RuleJudge


def build_script(
    *,
    rules: GameRules | None = None,
    truth: Truth | None = None,
) -> GameScript:
    """
    构造一个最小可判案剧本。

    这个测试文件只验证 RuleJudge + scoring 的接入效果：
    - 不测试 NPC
    - 不测试 CLI
    - 不测试线索搜索
    - 不测试 SessionRecorder

    核心目标：
    1. 旧的 60/40 写死规则不再生效。
    2. 默认评分变成 40/30/15/15。
    3. motive_keywords / method_keywords 参与评分。
    4. FinalVoteEvaluation 返回 score_breakdown。
    """

    return GameScript(
        id="mansion_murder_001",
        title="庄园谋杀案",
        version="v0.2.0",
        background="顾明远死在庄园书房中，现场有破碎红酒杯和多个可疑人物。",
        rules=rules
        or GameRules(
            max_question_rounds=5,
            allow_free_question=True,
            allow_clue_search=True,
            final_vote=[
                "suspect_character_id",
                "motive",
                "method",
                "key_evidence",
            ],
        ),
        characters=[
            Character(
                id="npc_doctor",
                name="周医生",
                role="私人医生",
                is_npc=True,
                public_profile="死者顾明远的私人医生，长期负责他的健康管理。",
            ),
            Character(
                id="npc_butler",
                name="林伯",
                role="管家",
                is_npc=True,
                public_profile="在顾家服务多年的老管家，熟悉庄园一切。",
            ),
            Character(
                id="npc_daughter",
                name="顾晓棠",
                role="死者女儿",
                is_npc=True,
                public_profile="顾明远的女儿，与父亲关系紧张。",
            ),
        ],
        npc_profiles=[],
        clues=[
            Clue(
                id="clue_broken_glass",
                title="破碎的红酒杯",
                content="死者手边有一只摔碎的红酒杯，杯底残留少量红酒。",
                visibility=ClueVisibility.PUBLIC,
                unlock_phase=GamePhase.START,
                related_character_ids=["npc_doctor"],
                is_key_clue=True,
                search_keywords=["红酒", "酒杯", "破碎"],
            ),
            Clue(
                id="clue_medicine_bottle",
                title="抽屉里的药瓶",
                content="书房抽屉中发现一个药瓶，瓶身标签显示为镇静剂。",
                visibility=ClueVisibility.LOCKED,
                unlock_phase=GamePhase.START,
                related_character_ids=["npc_doctor"],
                is_key_clue=True,
                search_keywords=["抽屉", "药瓶", "镇静剂"],
            ),
            Clue(
                id="clue_torn_letter",
                title="垃圾桶里的勒索信",
                content="垃圾桶中发现被撕碎的信件，内容显示死者长期勒索周医生。",
                visibility=ClueVisibility.LOCKED,
                unlock_phase=GamePhase.START,
                related_character_ids=["npc_doctor"],
                is_key_clue=True,
                search_keywords=["垃圾桶", "勒索信", "勒索"],
            ),
        ],
        truth=truth
        or Truth(
            # 当前项目旧协议中 truth.id 实际承担真凶 ID 的作用。
            # V0.2.0 新增 murderer_id，但仍保留 id 兼容旧剧本。
            id="npc_doctor",
            murderer_id="npc_doctor",
            motive="周医生被顾明远长期勒索。",
            method="将过量镇静剂混入红酒中，使顾明远逐渐失去意识并死亡。",
            key_clue_ids=[
                "clue_broken_glass",
                "clue_medicine_bottle",
                "clue_torn_letter",
            ],
            # V0.2.0 新增：动机和手法关键词。
            # 这些关键词用于确定性评分，避免“勒死”也能拿满分的问题。
            motive_keywords=["勒索"],
            method_keywords=["镇静剂", "红酒", "混入"],
            summary="周医生因被顾明远长期勒索，将过量镇静剂混入红酒中杀害顾明远。",
        ),
        timeline=[],
    )


def build_judge() -> RuleJudge:
    """
    构造默认 RuleJudge。

    默认剧本中：
    - 正确凶手：npc_doctor
    - 关键线索：clue_broken_glass / clue_medicine_bottle / clue_torn_letter
    - 动机关键词：勒索
    - 手法关键词：镇静剂 / 红酒 / 混入
    """

    return RuleJudge(build_script())


def test_evaluate_final_vote_all_correct():
    """
    全部正确时应得到满分。

    V0.2.0 默认评分：
    - 凶手：40
    - 关键线索：30
    - 动机：15
    - 手法：15

    总分：100
    """

    judge = build_judge()

    vote = FinalVote(
        suspect_character_id="npc_doctor",
        motive="周医生被顾明远长期勒索。",
        method="将过量镇静剂混入红酒中。",
        key_evidence=[
            "clue_broken_glass",
            "clue_medicine_bottle",
            "clue_torn_letter",
        ],
    )

    result = judge.evaluate_final_vote(vote)

    assert result.is_correct is True
    assert result.matched_murderer is True
    assert result.score == 100
    assert result.max_score == 100
    assert result.matched_key_clue_ids == [
        "clue_broken_glass",
        "clue_medicine_bottle",
        "clue_torn_letter",
    ]

    breakdown = result.score_breakdown

    assert breakdown["murderer"]["score"] == 40
    assert breakdown["key_evidence"]["score"] == 30
    assert breakdown["motive"]["score"] == 15
    assert breakdown["method"]["score"] == 15


def test_evaluate_final_vote_wrong_murderer():
    """
    凶手错误，但关键线索全命中。

    旧规则下：
    - 凶手错误
    - 关键线索全命中
    - 得 40 分

    新规则下：
    - 凶手：0
    - 关键线索：30
    - 动机：0，因为玩家动机没有命中“勒索”
    - 手法：0，因为玩家手法没有命中“镇静剂 / 红酒 / 混入”

    总分：30
    """

    judge = build_judge()

    vote = FinalVote(
        suspect_character_id="npc_butler",
        motive="管家不满顾明远变卖庄园。",
        method="使用备用钥匙进入书房作案。",
        key_evidence=[
            "clue_broken_glass",
            "clue_medicine_bottle",
            "clue_torn_letter",
        ],
    )

    result = judge.evaluate_final_vote(vote)

    assert result.is_correct is False
    assert result.matched_murderer is False
    assert result.score == 30

    breakdown = result.score_breakdown

    assert breakdown["murderer"]["score"] == 0
    assert breakdown["key_evidence"]["score"] == 30
    assert breakdown["motive"]["score"] == 0
    assert breakdown["method"]["score"] == 0


def test_evaluate_final_vote_partial_key_clues():
    """
    凶手、动机、手法正确，但关键线索只命中 1/3。

    默认关键证据分为 30。
    命中 1/3，则证据得 10 分。

    总分：
    - 凶手 40
    - 证据 10
    - 动机 15
    - 手法 15

    总分：80
    """

    judge = build_judge()

    vote = FinalVote(
        suspect_character_id="npc_doctor",
        motive="周医生被顾明远长期勒索。",
        method="将过量镇静剂混入红酒中。",
        key_evidence=[
            "clue_broken_glass",
        ],
    )

    result = judge.evaluate_final_vote(vote)

    assert result.is_correct is False
    assert result.matched_murderer is True
    assert result.score == 80

    breakdown = result.score_breakdown

    assert breakdown["murderer"]["score"] == 40
    assert breakdown["key_evidence"]["score"] == 10
    assert breakdown["motive"]["score"] == 15
    assert breakdown["method"]["score"] == 15

    assert breakdown["key_evidence"]["matched_clue_ids"] == ["clue_broken_glass"]
    assert breakdown["key_evidence"]["missing_clue_ids"] == [
        "clue_medicine_bottle",
        "clue_torn_letter",
    ]


def test_evaluate_final_vote_wrong_method_should_not_get_method_score():
    """
    回归 V0.1.3 的关键问题：

    玩家提交“勒死”时，不应该命中：
    - 镇静剂
    - 红酒
    - 混入

    即使凶手、关键线索、动机都正确，手法也必须是 0 分。
    """

    judge = build_judge()

    vote = FinalVote(
        suspect_character_id="npc_doctor",
        motive="周医生被顾明远长期勒索。",
        method="勒死",
        key_evidence=[
            "clue_broken_glass",
            "clue_medicine_bottle",
            "clue_torn_letter",
        ],
    )

    result = judge.evaluate_final_vote(vote)

    assert result.is_correct is False
    assert result.matched_murderer is True
    assert result.score == 85

    breakdown = result.score_breakdown

    assert breakdown["murderer"]["score"] == 40
    assert breakdown["key_evidence"]["score"] == 30
    assert breakdown["motive"]["score"] == 15
    assert breakdown["method"]["score"] == 0
    assert breakdown["method"]["matched_keywords"] == []
    assert breakdown["method"]["missing_keywords"] == ["镇静剂", "红酒", "混入"]


def test_evaluate_final_vote_from_game_runtime_state():
    """
    验证 RuleJudge 可以评估 GameRuntime 中保存的 final_vote。

    这个测试确保：
    - GameState.final_vote 的字段结构仍然兼容 RuleJudge
    - RuleJudge 不依赖 CLI 输入
    """

    script = build_script()
    state = GameState(script_id=script.id)

    state.final_vote = FinalVote(
        suspect_character_id="npc_doctor",
        motive="周医生被顾明远长期勒索。",
        method="将过量镇静剂混入红酒中。",
        key_evidence=[
            "clue_broken_glass",
            "clue_medicine_bottle",
            "clue_torn_letter",
        ],
    )

    judge = RuleJudge(script)
    result = judge.evaluate_final_vote(state.final_vote)

    assert result.is_correct is True
    assert result.score == 100
    assert result.score_breakdown["method"]["score"] == 15


def test_evaluate_final_vote_fallback_to_truth_id_when_murderer_id_missing():
    """
    兼容旧剧本：

    如果 truth.murderer_id 没有配置，
    RuleJudge 应该 fallback 到 truth.id。

    这样旧剧本不需要一次性全部迁移。
    """

    script = build_script(
        truth=Truth(
            id="npc_doctor",
            murderer_id=None,
            motive="周医生被顾明远长期勒索。",
            method="将过量镇静剂混入红酒中，使顾明远逐渐失去意识并死亡。",
            key_clue_ids=[
                "clue_broken_glass",
                "clue_medicine_bottle",
                "clue_torn_letter",
            ],
            motive_keywords=["勒索"],
            method_keywords=["镇静剂", "红酒", "混入"],
            summary="周医生因被顾明远长期勒索，将过量镇静剂混入红酒中杀害顾明远。",
        )
    )

    judge = RuleJudge(script)

    vote = FinalVote(
        suspect_character_id="npc_doctor",
        motive="勒索",
        method="镇静剂混入红酒",
        key_evidence=[
            "clue_broken_glass",
            "clue_medicine_bottle",
            "clue_torn_letter",
        ],
    )

    result = judge.evaluate_final_vote(vote)

    assert result.is_correct is True
    assert result.score == 100


def test_evaluate_final_vote_uses_custom_scoring_config():
    """
    验证 RuleJudge 使用 rules.scoring 自定义评分。

    自定义配置：
    - 凶手 50
    - 关键线索 20
    - 动机 10
    - 手法 20

    全部正确时仍然是 100，但 breakdown 应体现自定义权重。
    """

    script = build_script(
        rules=GameRules(
            max_question_rounds=5,
            allow_free_question=True,
            allow_clue_search=True,
            final_vote=[
                "suspect_character_id",
                "motive",
                "method",
                "key_evidence",
            ],
            scoring=ScoringRule(
                murderer_score=50,
                key_evidence_score=20,
                motive_score=10,
                method_score=20,
            ),
        )
    )

    judge = RuleJudge(script)

    vote = FinalVote(
        suspect_character_id="npc_doctor",
        motive="勒索",
        method="镇静剂混入红酒",
        key_evidence=[
            "clue_broken_glass",
            "clue_medicine_bottle",
            "clue_torn_letter",
        ],
    )

    result = judge.evaluate_final_vote(vote)

    assert result.is_correct is True
    assert result.score == 100

    breakdown = result.score_breakdown

    assert breakdown["murderer"]["score"] == 50
    assert breakdown["key_evidence"]["score"] == 20
    assert breakdown["motive"]["score"] == 10
    assert breakdown["method"]["score"] == 20


def test_evaluate_final_vote_unknown_character_should_raise():
    """
    玩家提交不存在的角色 ID 时，应直接报错。

    这是输入合法性问题，不应该进入评分流程。
    """

    judge = build_judge()

    vote = FinalVote(
        suspect_character_id="npc_unknown",
        motive="勒索",
        method="镇静剂混入红酒",
        key_evidence=[
            "clue_broken_glass",
        ],
    )

    with pytest.raises(ValueError, match="Unknown character_id"):
        judge.evaluate_final_vote(vote)


def test_evaluate_final_vote_unknown_clue_should_raise():
    """
    玩家提交不存在的 clue_id 时，应直接报错。

    这是输入合法性问题，不应该进入评分流程。
    """

    judge = build_judge()

    vote = FinalVote(
        suspect_character_id="npc_doctor",
        motive="勒索",
        method="镇静剂混入红酒",
        key_evidence=[
            "clue_not_exists",
        ],
    )

    with pytest.raises(ValueError, match="Unknown clue_id"):
        judge.evaluate_final_vote(vote)