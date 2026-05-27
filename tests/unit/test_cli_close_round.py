from types import SimpleNamespace

from stery.domain.enums import InvestigationRoundStatus
from stery.domain.state import GameState, InvestigationRound
from stery.interfaces.cli import MysteryCliApp


class FakeRuntime:
    def __init__(
        self,
        state: GameState | None,
        characters: list[SimpleNamespace] | None = None,
        close_error: Exception | None = None,
    ):
        self.state = state
        self.characters = characters or []
        self.close_error = close_error
        self.close_called = False

    def list_characters(self):
        return self.characters

    def close_current_round(self):
        self.close_called = True

        if self.close_error is not None:
            raise self.close_error

        if self.state is None:
            raise RuntimeError("Game has not started.")

        active_round = None
        for investigation_round in self.state.investigation_rounds:
            if investigation_round.round_id == self.state.active_round_id:
                active_round = investigation_round
                break

        if active_round is None:
            raise RuntimeError("No active investigation round")

        active_round.status = InvestigationRoundStatus.CLOSED

        new_round = InvestigationRound(
            round_no=active_round.round_no + 1,
            status=InvestigationRoundStatus.OPEN,
        )

        self.state.investigation_rounds.append(new_round)
        self.state.active_round_id = new_round.round_id

        return self.state


def build_app(
    state: GameState | None,
    close_error: Exception | None = None,
) -> tuple[MysteryCliApp, FakeRuntime]:
    runtime = FakeRuntime(
        state=state,
        close_error=close_error,
    )

    app = MysteryCliApp(
        runtime=runtime,
        npc_interaction_service=None,
        rule_judge=None,
        clue_search_service=None,
    )

    return app, runtime


def build_state_with_active_round() -> tuple[GameState, InvestigationRound]:
    state = GameState(script_id="snow_inn_murder")

    investigation_round = InvestigationRound(
        round_no=1,
        status=InvestigationRoundStatus.OPEN,
    )

    state.investigation_rounds.append(investigation_round)
    state.active_round_id = investigation_round.round_id

    return state, investigation_round


def test_close_round_when_game_not_started(capsys):
    app, runtime = build_app(state=None)

    app.close_round()

    captured = capsys.readouterr()

    assert "【关闭调查轮】" in captured.out
    assert "游戏尚未开始。" in captured.out
    assert runtime.close_called is False


def test_close_round_when_no_active_round(capsys):
    state = GameState(script_id="snow_inn_murder")
    app, runtime = build_app(state=state)

    app.close_round()

    captured = capsys.readouterr()

    assert "【关闭调查轮】" in captured.out
    assert "当前没有开启中的调查轮。" in captured.out
    assert runtime.close_called is False


def test_close_round_should_close_current_round_and_open_next_round(capsys):
    state, first_round = build_state_with_active_round()
    app, runtime = build_app(state=state)

    app.close_round()

    captured = capsys.readouterr()

    assert runtime.close_called is True

    assert "【关闭调查轮】" in captured.out
    assert "第 1 轮已关闭。" in captured.out
    assert "第 2 轮已开启。" in captured.out

    assert first_round.status == InvestigationRoundStatus.CLOSED
    assert len(state.investigation_rounds) == 2

    second_round = state.investigation_rounds[1]

    assert second_round.round_no == 2
    assert second_round.status == InvestigationRoundStatus.OPEN
    assert state.active_round_id == second_round.round_id


def test_close_round_should_print_error_when_runtime_close_failed(capsys):
    state, _ = build_state_with_active_round()
    app, runtime = build_app(
        state=state,
        close_error=ValueError("Game has already finished."),
    )

    app.close_round()

    captured = capsys.readouterr()

    assert runtime.close_called is True
    assert "【关闭调查轮】" in captured.out
    assert "关闭调查轮失败：Game has already finished." in captured.out