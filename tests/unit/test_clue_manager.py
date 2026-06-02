from pathlib import Path

import pytest

from stery.clue.clue_manager import ClueManager
from stery.script_repository import LocalFileScriptRepository

PROJECT_ROOT = Path(__file__).resolve().parents[2]

SCRIPT_PATH = "mansion_murder"

script = LocalFileScriptRepository().get_script(SCRIPT_PATH)
def test_get_initial_unlocked_clue_ids_only_contains_public_clues():
    clue_manager = ClueManager(script)

    unlocked_clue_ids = clue_manager.get_initial_unlocked_clue_ids()

    assert "clue_broken_glass" in unlocked_clue_ids
    assert "clue_medicine_bottle" not in unlocked_clue_ids
    assert "clue_torn_letter" not in unlocked_clue_ids


def test_list_available_clues_only_returns_unlocked_clues():
    clue_manager = ClueManager(script)
    from stery.domain.state import GameState
    from stery.domain.enums import GamePhase

    state = GameState(
        script_id=script.id,
        current_phase=GamePhase.BACKGROUND_INTRO,
        unlocked_clue_ids=clue_manager.get_initial_unlocked_clue_ids(),
    )

    clues = clue_manager.list_available_clues(state)
    clue_ids = {clue.id for clue in clues}

    assert "clue_broken_glass" in clue_ids
    assert "clue_medicine_bottle" not in clue_ids
    assert "clue_torn_letter" not in clue_ids


def test_unlock_clue_success():
    clue_manager = ClueManager(script)

    from stery.domain.state import GameState
    from stery.domain.enums import GamePhase

    state = GameState(
        script_id=script.id,
        current_phase=GamePhase.BACKGROUND_INTRO,
        unlocked_clue_ids=clue_manager.get_initial_unlocked_clue_ids(),
    )

    clue_manager.unlock_clue(state, "clue_medicine_bottle")

    clues = clue_manager.list_available_clues(state)
    clue_ids = {clue.id for clue in clues}

    assert "clue_medicine_bottle" in clue_ids


def test_unlock_unknown_clue_failed():
    clue_manager = ClueManager(script)

    from stery.domain.state import GameState
    from stery.domain.enums import GamePhase

    state = GameState(
        script_id=script.id,
        current_phase=GamePhase.BACKGROUND_INTRO,
        unlocked_clue_ids=clue_manager.get_initial_unlocked_clue_ids(),
    )

    with pytest.raises(ValueError, match="Unknown clue_id"):
        clue_manager.unlock_clue(state, "clue_not_exists")