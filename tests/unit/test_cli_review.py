from types import SimpleNamespace

from stery.domain.enums import InvestigationRoundStatus
from stery.domain.state import (
    GameState,
    InvestigationRound,
    NPCAnswerRecord,
    QuestionRecord,
)
from stery.interfaces.cli import MysteryCliApp


class FakeRuntime:
    def __init__(
        self,
        state: GameState | None,
        characters: list[SimpleNamespace] | None = None,
    ):
        self.state = state
        self.characters = characters or []

    def list_characters(self):
        return self.characters


def build_app(
    state: GameState | None,
    characters: list[SimpleNamespace] | None = None,
) -> MysteryCliApp:
    return MysteryCliApp(
        runtime=FakeRuntime(state=state, characters=characters),
        npc_interaction_service=None,
        rule_judge=None,
        clue_search_service=None,
    )


def build_state_with_active_round() -> tuple[GameState, InvestigationRound]:
    state = GameState(script_id="snow_inn_murder")

    investigation_round = InvestigationRound(
        round_no=1,
        status=InvestigationRoundStatus.OPEN,
    )

    state.investigation_rounds.append(investigation_round)
    state.active_round_id = investigation_round.round_id

    return state, investigation_round


def test_show_review_when_game_not_started(capsys):
    app = build_app(state=None)

    app.show_review()

    captured = capsys.readouterr()

    assert "【当前调查轮摘要】" in captured.out
    assert "游戏尚未开始。" in captured.out


def test_show_review_when_no_active_round(capsys):
    state = GameState(script_id="snow_inn_murder")
    app = build_app(state=state)

    app.show_review()

    captured = capsys.readouterr()

    assert "【当前调查轮摘要】" in captured.out
    assert "当前没有开启中的调查轮。" in captured.out


def test_show_review_when_active_round_has_no_questions(capsys):
    state, _ = build_state_with_active_round()

    app = build_app(state=state)

    app.show_review()

    captured = capsys.readouterr()

    assert "【当前调查轮摘要】" in captured.out
    assert "调查轮次：第 1 轮" in captured.out
    assert "轮次状态：OPEN" in captured.out
    assert "本轮提问次数：0" in captured.out
    assert "本轮回答次数：0" in captured.out
    assert "当前总提问次数：0" in captured.out
    assert "【本轮已询问 NPC】" in captured.out
    assert "暂无已询问 NPC。" in captured.out
    assert "【本轮问答】" in captured.out
    assert "暂无问答记录。" in captured.out


def test_show_review_should_display_current_round_questions_and_answers(capsys):
    state, investigation_round = build_state_with_active_round()

    question = QuestionRecord(
        target_character_id="npc_pharmacist",
        content="你是谁？",
    )
    answer = NPCAnswerRecord(
        question_id=question.question_id,
        target_character_id="npc_pharmacist",
        content="我是程曼，诊所的药剂师。",
    )

    state.question_history.append(question)
    state.answer_history.append(answer)
    investigation_round.question_ids.append(question.question_id)

    characters = [
        SimpleNamespace(
            id="npc_pharmacist",
            name="程曼",
        )
    ]

    app = build_app(
        state=state,
        characters=characters,
    )

    app.show_review()

    captured = capsys.readouterr()

    assert "【当前调查轮摘要】" in captured.out
    assert "调查轮次：第 1 轮" in captured.out
    assert "轮次状态：OPEN" in captured.out
    assert "本轮提问次数：1" in captured.out
    assert "本轮回答次数：1" in captured.out
    assert "当前总提问次数：1" in captured.out

    assert "【本轮已询问 NPC】" in captured.out
    assert "- 程曼（npc_pharmacist）：1 次" in captured.out

    assert "【本轮问答】" in captured.out
    assert "[1] 询问 NPC：程曼（npc_pharmacist）" in captured.out
    assert "玩家：你是谁？" in captured.out
    assert "NPC：我是程曼，诊所的药剂师。" in captured.out


def test_show_review_should_only_display_active_round_questions(capsys):
    state = GameState(script_id="snow_inn_murder")

    first_round = InvestigationRound(
        round_no=1,
        status=InvestigationRoundStatus.CLOSED,
    )
    second_round = InvestigationRound(
        round_no=2,
        status=InvestigationRoundStatus.OPEN,
    )

    first_question = QuestionRecord(
        target_character_id="npc_pharmacist",
        content="第一轮问题",
    )
    second_question = QuestionRecord(
        target_character_id="npc_photographer",
        content="第二轮问题",
    )

    first_answer = NPCAnswerRecord(
        question_id=first_question.question_id,
        target_character_id="npc_pharmacist",
        content="第一轮回答",
    )
    second_answer = NPCAnswerRecord(
        question_id=second_question.question_id,
        target_character_id="npc_photographer",
        content="第二轮回答",
    )

    state.question_history.extend([first_question, second_question])
    state.answer_history.extend([first_answer, second_answer])

    first_round.question_ids.append(first_question.question_id)
    second_round.question_ids.append(second_question.question_id)

    state.investigation_rounds.extend([first_round, second_round])
    state.active_round_id = second_round.round_id

    characters = [
        SimpleNamespace(
            id="npc_pharmacist",
            name="程曼",
        ),
        SimpleNamespace(
            id="npc_photographer",
            name="陆青",
        ),
    ]

    app = build_app(
        state=state,
        characters=characters,
    )

    app.show_review()

    captured = capsys.readouterr()

    assert "调查轮次：第 2 轮" in captured.out
    assert "本轮提问次数：1" in captured.out
    assert "本轮回答次数：1" in captured.out

    assert "第二轮问题" in captured.out
    assert "第二轮回答" in captured.out
    assert "陆青（npc_photographer）" in captured.out

    assert "第一轮问题" not in captured.out
    assert "第一轮回答" not in captured.out
    assert "程曼（npc_pharmacist）：1 次" not in captured.out


def test_show_review_should_handle_missing_answer(capsys):
    state, investigation_round = build_state_with_active_round()

    question = QuestionRecord(
        target_character_id="npc_photographer",
        content="你在这里干什么？",
    )

    state.question_history.append(question)
    investigation_round.question_ids.append(question.question_id)

    characters = [
        SimpleNamespace(
            id="npc_photographer",
            name="陆青",
        )
    ]

    app = build_app(
        state=state,
        characters=characters,
    )

    app.show_review()

    captured = capsys.readouterr()

    assert "【当前调查轮摘要】" in captured.out
    assert "本轮提问次数：1" in captured.out
    assert "本轮回答次数：0" in captured.out
    assert "- 陆青（npc_photographer）：1 次" in captured.out
    assert "[1] 询问 NPC：陆青（npc_photographer）" in captured.out
    assert "玩家：你在这里干什么？" in captured.out
    assert "NPC：<暂无回答记录>" in captured.out