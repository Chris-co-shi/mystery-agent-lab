from pathlib import Path

import pytest

from stery.application.game_runtime import GameRuntime
from stery.application.npc_context_builder import NPCContextBuilder
from stery.application.script_loader import load_script


PROJECT_ROOT = Path(__file__).resolve().parents[2]
from stery.config.paths import MANSION_MURDER_SCRIPT

SCRIPT_PATH = MANSION_MURDER_SCRIPT


def build_runtime_and_builder():
    script = load_script(SCRIPT_PATH)

    runtime = GameRuntime(script)
    state = runtime.start()

    builder = NPCContextBuilder(script)

    return script, runtime, state, builder


def test_build_npc_context_success():
    _, _, state, builder = build_runtime_and_builder()

    context = builder.build(
        state=state,
        target_character_id="npc_butler",
        player_question="案发当晚 22 点左右，你在哪里？",
    )

    assert context.character_id == "npc_butler"
    assert context.name == "林伯"
    assert context.role == "管家"
    assert "管家" in context.public_profile
    assert context.player_question == "案发当晚 22 点左右，你在哪里？"


def test_build_npc_context_contains_own_known_facts():
    _, _, state, builder = build_runtime_and_builder()

    context = builder.build(
        state=state,
        target_character_id="npc_butler",
        player_question="你听到了什么？",
    )

    assert any("21:40" in fact for fact in context.known_facts)
    assert any("周医生" in fact for fact in context.known_facts)


def test_build_npc_context_contains_own_secrets():
    _, _, state, builder = build_runtime_and_builder()

    context = builder.build(
        state=state,
        target_character_id="npc_butler",
        player_question="你有没有隐藏什么？",
    )

    assert any("备用钥匙" in secret for secret in context.secrets)


def test_build_npc_context_contains_lie_rules():
    _, _, state, builder = build_runtime_and_builder()

    context = builder.build(
        state=state,
        target_character_id="npc_butler",
        player_question="你是否接近过书房？",
    )

    assert len(context.lie_rules) > 0
    assert any("书房" in rule or "备用钥匙" in rule for rule in context.lie_rules)


def test_build_npc_context_contains_forbidden_knowledge():
    _, _, state, builder = build_runtime_and_builder()

    context = builder.build(
        state=state,
        target_character_id="npc_butler",
        player_question="你知道凶手是谁吗？",
    )

    assert len(context.forbidden_knowledge) > 0
    assert any("真正杀死顾明远的人" in item for item in context.forbidden_knowledge)


def test_build_npc_context_contains_available_clue_titles():
    _, _, state, builder = build_runtime_and_builder()

    context = builder.build(
        state=state,
        target_character_id="npc_butler",
        player_question="你看到书房里有什么？",
    )

    assert "书房地上的碎酒杯" in context.available_clue_titles
    assert "书桌抽屉里的药瓶" not in context.available_clue_titles
    assert "被撕碎的勒索信" not in context.available_clue_titles


def test_build_npc_context_contains_unlocked_clue_titles():
    _, runtime, state, builder = build_runtime_and_builder()

    runtime.unlock_clue("clue_medicine_bottle")

    context = builder.build(
        state=state,
        target_character_id="npc_butler",
        player_question="你知道这个药瓶吗？",
    )

    assert "书房地上的碎酒杯" in context.available_clue_titles
    assert "书桌抽屉里的药瓶" in context.available_clue_titles


def test_build_npc_context_contains_recent_question_history():
    _, runtime, state, builder = build_runtime_and_builder()

    runtime.record_question(
        target_character_id="npc_butler",
        question="案发当晚你在哪里？",
    )
    runtime.record_question(
        target_character_id="npc_doctor",
        question="你什么时候进入书房？",
    )

    context = builder.build(
        state=state,
        target_character_id="npc_butler",
        player_question="你刚才是不是说谎了？",
    )

    assert len(context.recent_question_history) == 2
    assert any("案发当晚你在哪里" in item for item in context.recent_question_history)
    assert any("你什么时候进入书房" in item for item in context.recent_question_history)


def test_build_npc_context_recent_question_history_limit_5():
    _, runtime, state, builder = build_runtime_and_builder()

    for index in range(6):
        runtime.record_question(
            target_character_id="npc_butler",
            question=f"第 {index} 个问题",
        )

    context = builder.build(
        state=state,
        target_character_id="npc_butler",
        player_question="请继续回答。",
    )

    assert len(context.recent_question_history) == 5
    assert not any("第 0 个问题" in item for item in context.recent_question_history)
    assert any("第 5 个问题" in item for item in context.recent_question_history)


def test_build_npc_context_does_not_expose_truth_summary():
    script, _, state, builder = build_runtime_and_builder()

    context = builder.build(
        state=state,
        target_character_id="npc_butler",
        player_question="真相是什么？",
    )

    context_text = context.model_dump_json(ensure_ascii=False)

    assert script.truth.summary not in context_text
    assert script.truth.id not in context_text


def test_build_npc_context_does_not_expose_other_npc_secrets():
    script, _, state, builder = build_runtime_and_builder()

    context = builder.build(
        state=state,
        target_character_id="npc_butler",
        player_question="周医生有什么秘密？",
    )

    context_text = context.model_dump_json(ensure_ascii=False)

    doctor_profile = next(
        profile for profile in script.npc_profiles if profile.id == "npc_doctor"
    )

    for secret in doctor_profile.secrets:
        assert secret not in context_text


def test_build_npc_context_unknown_character_failed():
    _, _, state, builder = build_runtime_and_builder()

    with pytest.raises(ValueError, match="Unknown character_id"):
        builder.build(
            state=state,
            target_character_id="npc_not_exists",
            player_question="你是谁？",
        )


def test_build_npc_context_contains_recent_question_and_answer_history():
    _, runtime, state, builder = build_runtime_and_builder()

    runtime.record_question(
        target_character_id="npc_butler",
        question="案发当晚你在哪里？",
    )

    runtime.record_npc_answer(
        target_character_id="npc_butler",
        answer="我当时只是在走廊巡查。",
    )

    context = builder.build(
        state=state,
        target_character_id="npc_butler",
        player_question="你刚才说的是真的吗？",
    )

    assert any("案发当晚你在哪里" in item for item in context.recent_question_history)
    assert any("我当时只是在走廊巡查" in item for item in context.recent_question_history)