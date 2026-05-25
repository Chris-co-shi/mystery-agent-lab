from pathlib import Path

import pytest

from stery.application.clue_search_service import ClueSearchService
from stery.application.game_runtime import GameRuntime
from stery.application.script_loader import load_script


PROJECT_ROOT = Path(__file__).resolve().parents[2]
SCRIPT_PATH = PROJECT_ROOT / "scripts" / "mansion_murder.json"


def build_service_and_state():
    script = load_script(SCRIPT_PATH)
    runtime = GameRuntime(script)
    state = runtime.start()
    service = ClueSearchService(script)
    return service, state


def test_search_unlocks_locked_clue():
    service, state = build_service_and_state()

    result = service.search(state, "抽屉")

    assert len(result.unlocked_clues) == 1
    assert result.unlocked_clues[0].id == "clue_medicine_bottle"
    assert "clue_medicine_bottle" in state.unlocked_clue_ids


def test_search_known_clue_twice_returns_already_unlocked():
    service, state = build_service_and_state()

    service.search(state, "抽屉")
    result = service.search(state, "抽屉")

    assert len(result.unlocked_clues) == 0
    assert len(result.already_unlocked_clues) == 1
    assert result.already_unlocked_clues[0].id == "clue_medicine_bottle"


def test_search_empty_keyword_failed():
    service, state = build_service_and_state()

    with pytest.raises(ValueError, match="Search keyword cannot be empty"):
        service.search(state, "")


def test_search_unknown_keyword_returns_no_new_clue():
    service, state = build_service_and_state()

    result = service.search(state, "不存在的地点")

    assert len(result.unlocked_clues) == 0
    assert len(result.already_unlocked_clues) == 0
    assert result.message == "没有发现新的线索。"