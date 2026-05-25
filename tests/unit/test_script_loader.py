from pathlib import Path

import pytest

from stery.application import load_script
from stery.domain.models import GameScript

PROJECT_ROOT = Path(__file__).resolve().parents[2]
from stery.config.paths import MANSION_MURDER_SCRIPT

SCRIPT_PATH = MANSION_MURDER_SCRIPT


def test_load_mansion_murder_script_success():
    script = load_script(SCRIPT_PATH)

    assert isinstance(script, GameScript)
    assert script.id == "mansion_murder_001"
    assert script.title == "庄园夜宴谋杀案"
    assert script.truth.id == "npc_doctor"

    assert len(script.characters) == 3
    assert len(script.npc_profiles) == 3
    assert len(script.clues) >= 5
    assert len(script.timeline) >= 3


def test_load_script_file_not_found():
    not_exists_path = PROJECT_ROOT / "data" / "scripts" / "not_exists.json"

    with pytest.raises(FileNotFoundError):
        load_script(not_exists_path)