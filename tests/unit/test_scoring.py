# tests/judge/test_scoring.py

from stery.judge.scoring import (
    ScoringConfig,
    build_score_breakdown,
    score_key_evidence,
    score_keywords,
    score_murderer,
)


def test_scoring_config_uses_default_when_rules_missing():
    scoring = ScoringConfig.from_rules(None)

    assert scoring.murderer_score == 40
    assert scoring.key_evidence_score == 30
    assert scoring.motive_score == 15
    assert scoring.method_score == 15
    assert scoring.total_score == 100
    assert scoring.validate() == []


def test_scoring_config_uses_default_when_scoring_missing():
    scoring = ScoringConfig.from_rules({})

    assert scoring.murderer_score == 40
    assert scoring.key_evidence_score == 30
    assert scoring.motive_score == 15
    assert scoring.method_score == 15
    assert scoring.total_score == 100
    assert scoring.validate() == []


def test_scoring_config_can_read_custom_scoring_from_dict():
    scoring = ScoringConfig.from_rules(
        {
            "scoring": {
                "murderer_score": 50,
                "key_evidence_score": 20,
                "motive_score": 10,
                "method_score": 20,
            }
        }
    )

    assert scoring.murderer_score == 50
    assert scoring.key_evidence_score == 20
    assert scoring.motive_score == 10
    assert scoring.method_score == 20
    assert scoring.total_score == 100
    assert scoring.validate() == []


def test_scoring_config_validate_reports_non_100_total_score():
    scoring = ScoringConfig(
        murderer_score=40,
        key_evidence_score=30,
        motive_score=15,
        method_score=10,
    )

    errors = scoring.validate()

    assert len(errors) == 1
    assert "总分建议为 100" in errors[0]


def test_scoring_config_validate_reports_non_positive_score():
    scoring = ScoringConfig(
        murderer_score=40,
        key_evidence_score=30,
        motive_score=15,
        method_score=0,
    )

    errors = scoring.validate()

    assert len(errors) == 2
    assert any("method_score 必须大于 0" in error for error in errors)
    assert any("总分建议为 100" in error for error in errors)


def test_score_murderer_gets_full_score_when_matched():
    result = score_murderer(
        actual_murderer_id="npc_doctor",
        expected_murderer_id="npc_doctor",
        max_score=40,
    )

    assert result.score == 40
    assert result.max_score == 40
    assert result.matched is True


def test_score_murderer_gets_zero_when_not_matched():
    result = score_murderer(
        actual_murderer_id="npc_butler",
        expected_murderer_id="npc_doctor",
        max_score=40,
    )

    assert result.score == 0
    assert result.max_score == 40
    assert result.matched is False


def test_score_key_evidence_scores_by_ratio():
    result = score_key_evidence(
        actual_clue_ids=["clue_a", "clue_c"],
        expected_clue_ids=["clue_a", "clue_b", "clue_c"],
        max_score=30,
    )

    assert result.score == 20
    assert set(result.matched_clue_ids) == {"clue_a", "clue_c"}
    assert result.missing_clue_ids == ["clue_b"]
    assert "命中 2/3" in result.reason


def test_score_key_evidence_deduplicates_actual_clues():
    result = score_key_evidence(
        actual_clue_ids=["clue_a", "clue_a", "clue_b"],
        expected_clue_ids=["clue_a", "clue_b", "clue_c"],
        max_score=30,
    )

    assert result.score == 20
    assert set(result.matched_clue_ids) == {"clue_a", "clue_b"}
    assert result.missing_clue_ids == ["clue_c"]


def test_score_key_evidence_gets_zero_when_expected_empty():
    result = score_key_evidence(
        actual_clue_ids=["clue_a"],
        expected_clue_ids=[],
        max_score=30,
    )

    assert result.score == 0
    assert result.matched_clue_ids == []
    assert result.missing_clue_ids == []


def test_score_key_evidence_uses_half_up_rounding():
    result = score_key_evidence(
        actual_clue_ids=["clue_a"],
        expected_clue_ids=["clue_a", "clue_b"],
        max_score=15,
    )

    assert result.score == 8


def test_score_keywords_gets_full_score_when_all_keywords_matched():
    result = score_keywords(
        actual_text="凶手把镇静剂混入红酒中完成投药",
        expected_keywords=["镇静剂", "红酒", "投药"],
        max_score=15,
        label="手法关键词",
    )

    assert result.score == 15
    assert result.matched_keywords == ["镇静剂", "红酒", "投药"]
    assert result.missing_keywords == []
    assert "命中 3/3" in result.reason


def test_score_keywords_scores_by_ratio():
    result = score_keywords(
        actual_text="凶手把镇静剂放入红酒",
        expected_keywords=["镇静剂", "红酒", "投药"],
        max_score=15,
        label="手法关键词",
    )

    assert result.score == 10
    assert result.matched_keywords == ["镇静剂", "红酒"]
    assert result.missing_keywords == ["投药"]
    assert "缺失「投药」" in result.reason


def test_score_keywords_uses_half_up_rounding():
    result = score_keywords(
        actual_text="凶手使用药物",
        expected_keywords=["药物", "酒"],
        max_score=15,
        label="手法关键词",
    )

    assert result.score == 8


def test_wrong_method_strangling_does_not_match_poison_keywords():
    result = score_keywords(
        actual_text="勒死",
        expected_keywords=["镇静剂", "红酒", "投药"],
        max_score=15,
        label="手法关键词",
    )

    assert result.score == 0
    assert result.matched_keywords == []
    assert result.missing_keywords == ["镇静剂", "红酒", "投药"]
    assert "命中「无」" in result.reason
    assert "缺失「镇静剂、红酒、投药」" in result.reason


def test_score_keywords_uses_fallback_text_when_keywords_missing():
    result = score_keywords(
        actual_text="被死者长期勒索",
        expected_keywords=[],
        fallback_expected_text="被死者长期勒索",
        max_score=15,
        label="动机关键词",
    )

    assert result.score == 15
    assert result.matched_keywords == ["被死者长期勒索"]
    assert result.missing_keywords == []


def test_score_keywords_fallback_text_not_matched():
    result = score_keywords(
        actual_text="因为遗产纠纷",
        expected_keywords=[],
        fallback_expected_text="被死者长期勒索",
        max_score=15,
        label="动机关键词",
    )

    assert result.score == 0
    assert result.matched_keywords == []
    assert result.missing_keywords == ["被死者长期勒索"]


def test_score_keywords_gets_zero_when_no_keywords_and_no_fallback():
    result = score_keywords(
        actual_text="任意文本",
        expected_keywords=[],
        fallback_expected_text=None,
        max_score=15,
        label="动机关键词",
    )

    assert result.score == 0
    assert result.matched_keywords == []
    assert result.missing_keywords == []


def test_build_score_breakdown_returns_total_score():
    scoring = ScoringConfig.default()

    breakdown = build_score_breakdown(
        scoring=scoring,
        actual_murderer_id="npc_doctor",
        expected_murderer_id="npc_doctor",
        actual_key_evidence_ids=["clue_wine", "clue_lip"],
        expected_key_evidence_ids=["clue_wine", "clue_lip"],
        actual_motive="被死者勒索",
        motive_keywords=["勒索"],
        actual_method="把镇静剂混入红酒投药",
        method_keywords=["镇静剂", "红酒", "投药"],
        expected_motive="被死者长期勒索",
        expected_method="将镇静剂混入红酒中投药",
    )

    assert breakdown.total_score == 100
    assert breakdown.max_score == 100
    assert breakdown.murderer.score == 40
    assert breakdown.key_evidence.score == 30
    assert breakdown.motive.score == 15
    assert breakdown.method.score == 15


def test_build_score_breakdown_exposes_method_error():
    scoring = ScoringConfig.default()

    breakdown = build_score_breakdown(
        scoring=scoring,
        actual_murderer_id="npc_doctor",
        expected_murderer_id="npc_doctor",
        actual_key_evidence_ids=["clue_wine", "clue_lip"],
        expected_key_evidence_ids=["clue_wine", "clue_lip"],
        actual_motive="被死者勒索",
        motive_keywords=["勒索"],
        actual_method="勒死",
        method_keywords=["镇静剂", "红酒", "投药"],
        expected_motive="被死者长期勒索",
        expected_method="将镇静剂混入红酒中投药",
    )

    assert breakdown.total_score == 85
    assert breakdown.murderer.score == 40
    assert breakdown.key_evidence.score == 30
    assert breakdown.motive.score == 15
    assert breakdown.method.score == 0
    assert breakdown.method.matched_keywords == []
    assert breakdown.method.missing_keywords == ["镇静剂", "红酒", "投药"]


def test_score_breakdown_to_dict_contains_explainable_fields():
    scoring = ScoringConfig.default()

    breakdown = build_score_breakdown(
        scoring=scoring,
        actual_murderer_id="npc_butler",
        expected_murderer_id="npc_doctor",
        actual_key_evidence_ids=["clue_wine"],
        expected_key_evidence_ids=["clue_wine", "clue_lip"],
        actual_motive="被死者勒索",
        motive_keywords=["勒索"],
        actual_method="勒死",
        method_keywords=["镇静剂", "红酒", "投药"],
    )

    data = breakdown.to_dict()

    assert data["total_score"] == 30
    assert data["max_score"] == 100

    assert data["murderer"]["score"] == 0
    assert data["murderer"]["max_score"] == 40
    assert data["murderer"]["matched"] is False
    assert "reason" in data["murderer"]

    assert data["key_evidence"]["score"] == 15
    assert data["key_evidence"]["max_score"] == 30
    assert data["key_evidence"]["matched_clue_ids"] == ["clue_wine"]
    assert data["key_evidence"]["missing_clue_ids"] == ["clue_lip"]
    assert "reason" in data["key_evidence"]

    assert data["motive"]["score"] == 15
    assert data["method"]["score"] == 0
    assert data["method"]["missing_keywords"] == ["镇静剂", "红酒", "投药"]


def test_score_key_evidence_preserves_expected_order():
    """
    关键证据返回顺序应跟随 expected_clue_ids。

    原因：
    truth.key_evidence_ids 的顺序通常来自剧本作者设计，
    比简单字母排序更适合后续展示。
    """

    result = score_key_evidence(
        actual_clue_ids=["clue_c", "clue_a"],
        expected_clue_ids=["clue_a", "clue_b", "clue_c"],
        max_score=30,
    )

    assert result.score == 20
    assert result.matched_clue_ids == ["clue_a", "clue_c"]
    assert result.missing_clue_ids == ["clue_b"]