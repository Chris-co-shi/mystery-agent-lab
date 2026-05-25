import json
from copy import deepcopy
from pathlib import Path

import pytest

from stery.application.script_validator import validate_script_references
from stery.domain.models import GameScript

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SCRIPT_PATH = PROJECT_ROOT  / "scripts" / "mansion_murder.json"


def load_script_data() -> dict:
    return json.loads(SCRIPT_PATH.read_text(encoding="utf-8"))


def build_script(data: dict) -> GameScript:
    return GameScript.model_validate(data)


def test_validate_script_references_success():
    data = load_script_data()
    script = build_script(data)

    validate_script_references(script)


def test_truth_murderer_must_exist():
    data = deepcopy(load_script_data())
    data["truth"]["id"] = "npc_not_exists"

    script = build_script(data)

    with pytest.raises(ValueError, match="id"):
        validate_script_references(script)


def test_truth_key_clues_must_exist():
    data = deepcopy(load_script_data())
    data["truth"]["key_clue_ids"].append("clue_not_exists")

    script = build_script(data)

    with pytest.raises(ValueError, match="key clue_id"):
        validate_script_references(script)


def test_npc_profile_character_must_exist():
    data = deepcopy(load_script_data())
    data["npc_profiles"][0]["id"] = "npc_not_exists"

    script = build_script(data)

    with pytest.raises(ValueError, match="NPC Profile"):
        validate_script_references(script)


def test_clue_related_character_must_exist():
    data = deepcopy(load_script_data())
    data["clues"][0]["related_character_ids"].append("npc_not_exists")

    script = build_script(data)

    with pytest.raises(ValueError, match="Clue"):
        validate_script_references(script)


def test_timeline_character_must_exist():
    data = deepcopy(load_script_data())
    data["timeline"][0]["id"] = "npc_not_exists"

    script = build_script(data)

    with pytest.raises(ValueError, match="Timeline"):
        validate_script_references(script)