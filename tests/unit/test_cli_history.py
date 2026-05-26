from stery.domain.state import GameState, NPCAnswerRecord, QuestionRecord
from stery.interfaces.cli import MysteryCliApp


class FakeRuntime:
    def __init__(self, state: GameState | None):
        self.state = state


def build_app(state: GameState | None) -> MysteryCliApp:
    return MysteryCliApp(
        runtime=FakeRuntime(state),
        npc_interaction_service=None,
        rule_judge=None,
        clue_search_service=None,
    )


def test_show_history_when_game_not_started(capsys):
    app = build_app(state=None)

    app.show_history()

    captured = capsys.readouterr()

    assert "【问答历史】" in captured.out
    assert "游戏尚未开始。" in captured.out


def test_show_history_when_no_history(capsys):
    state = GameState(script_id="snow_inn_murder")
    app = build_app(state)

    app.show_history()

    captured = capsys.readouterr()

    assert "【问答历史】" in captured.out
    assert "暂无问答记录。" in captured.out


def test_show_history_should_display_question_and_answer(capsys):
    state = GameState(script_id="snow_inn_murder")

    question = QuestionRecord(
        target_character_id="npc_pharmacist",
        content="你是谁",
    )
    answer = NPCAnswerRecord(
        question_id=question.question_id,
        target_character_id="npc_pharmacist",
        content="我是程曼，诊所的药剂师。",
    )

    state.question_history.append(question)
    state.answer_history.append(answer)

    app = build_app(state)

    app.show_history()

    captured = capsys.readouterr()

    assert "【问答历史】" in captured.out
    assert "[1] 询问 NPC：npc_pharmacist" in captured.out
    assert "玩家：你是谁" in captured.out
    assert "NPC：我是程曼，诊所的药剂师。" in captured.out


def test_show_history_should_handle_missing_answer(capsys):
    state = GameState(script_id="snow_inn_murder")

    question = QuestionRecord(
        target_character_id="npc_photographer",
        content="你在这里干什么？",
    )

    state.question_history.append(question)

    app = build_app(state)

    app.show_history()

    captured = capsys.readouterr()

    assert "【问答历史】" in captured.out
    assert "[1] 询问 NPC：npc_photographer" in captured.out
    assert "玩家：你在这里干什么？" in captured.out
    assert "NPC：<暂无回答记录>" in captured.out