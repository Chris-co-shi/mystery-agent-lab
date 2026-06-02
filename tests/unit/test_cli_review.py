from types import SimpleNamespace

from stery.domain.state import (
    GameState,
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





def test_show_review_when_game_not_started(capsys):
    app = build_app(state=None)

    app.show_review()

    captured = capsys.readouterr()

    assert "【调查摘要】" in captured.out
    assert "游戏尚未开始。" in captured.out


def test_show_review_when_no_questions(capsys):
    state = GameState(script_id="snow_inn_murder")
    app = build_app(state=state)

    app.show_review()

    captured = capsys.readouterr()

    assert "【调查摘要】" in captured.out
    assert "暂无已询问 NPC。" in captured.out
    assert "暂无问答记录。" in captured.out





