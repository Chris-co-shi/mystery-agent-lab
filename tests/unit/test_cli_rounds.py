from stery.domain.enums import InvestigationRoundStatus
from stery.domain.state import GameState, InvestigationRound, QuestionRecord
from stery.interfaces.cli import MysteryCliApp


class FakeRuntime:
    def __init__(self, state: GameState | None):
        self.state = state


def build_app(state: GameState | None) -> MysteryCliApp:
    return MysteryCliApp(
        runtime=FakeRuntime(state=state),
        npc_interaction_service=None,
        rule_judge=None,
        clue_search_service=None,
    )


def test_show_rounds_when_game_not_started(capsys):
    app = build_app(state=None)

    app.show_rounds()

    captured = capsys.readouterr()

    assert "【调查轮次列表】" in captured.out
    assert "游戏尚未开始。" in captured.out


def test_show_rounds_when_no_rounds(capsys):
    state = GameState(script_id="snow_inn_murder")
    app = build_app(state=state)

    app.show_rounds()

    captured = capsys.readouterr()

    assert "【调查轮次列表】" in captured.out
    assert "暂无调查轮记录。" in captured.out


def test_show_rounds_should_display_single_open_round(capsys):
    state = GameState(script_id="snow_inn_murder")

    investigation_round = InvestigationRound(
        round_no=1,
        status=InvestigationRoundStatus.OPEN,
    )

    state.investigation_rounds.append(investigation_round)
    state.active_round_id = investigation_round.round_id

    app = build_app(state=state)

    app.show_rounds()

    captured = capsys.readouterr()

    assert "【调查轮次列表】" in captured.out
    assert "第 1 轮：OPEN，提问 0 次（当前）" in captured.out


def test_show_rounds_should_display_question_count(capsys):
    state = GameState(script_id="snow_inn_murder")

    investigation_round = InvestigationRound(
        round_no=1,
        status=InvestigationRoundStatus.OPEN,
    )

    first_question = QuestionRecord(
        target_character_id="npc_pharmacist",
        content="你是谁？",
    )
    second_question = QuestionRecord(
        target_character_id="npc_photographer",
        content="你在这里干什么？",
    )

    state.question_history.extend([first_question, second_question])
    investigation_round.question_ids.extend(
        [
            first_question.question_id,
            second_question.question_id,
        ]
    )

    state.investigation_rounds.append(investigation_round)
    state.active_round_id = investigation_round.round_id

    app = build_app(state=state)

    app.show_rounds()

    captured = capsys.readouterr()

    assert "【调查轮次列表】" in captured.out
    assert "第 1 轮：OPEN，提问 2 次（当前）" in captured.out


def test_show_rounds_should_display_closed_and_current_rounds(capsys):
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

    first_round.question_ids.append(first_question.question_id)
    second_round.question_ids.append(second_question.question_id)

    state.question_history.extend([first_question, second_question])
    state.investigation_rounds.extend([first_round, second_round])
    state.active_round_id = second_round.round_id

    app = build_app(state=state)

    app.show_rounds()

    captured = capsys.readouterr()

    assert "【调查轮次列表】" in captured.out
    assert "第 1 轮：CLOSED，提问 1 次" in captured.out
    assert "第 1 轮：CLOSED，提问 1 次（当前）" not in captured.out

    assert "第 2 轮：OPEN，提问 1 次（当前）" in captured.out


def test_show_rounds_should_not_mark_any_round_when_active_round_missing(capsys):
    state = GameState(script_id="snow_inn_murder")

    investigation_round = InvestigationRound(
        round_no=1,
        status=InvestigationRoundStatus.CLOSED,
    )

    state.investigation_rounds.append(investigation_round)
    state.active_round_id = None

    app = build_app(state=state)

    app.show_rounds()

    captured = capsys.readouterr()

    assert "【调查轮次列表】" in captured.out
    assert "第 1 轮：CLOSED，提问 0 次" in captured.out
    assert "（当前）" not in captured.out