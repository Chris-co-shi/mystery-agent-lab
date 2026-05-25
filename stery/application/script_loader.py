import json
from pathlib import Path

from stery.application.script_validator import validate_script_references
from stery.domain.models import GameScript


def load_script(path: str | Path) -> GameScript:
    """
    加载剧本。

    :param path:
    :return: 剧本对象
    """
    script_path = Path(path)
    if not script_path.exists():
        raise ValueError(f"Unknown script_id: {path}")

    data = json.loads(script_path.read_text(encoding="utf-8"))
    script = GameScript.model_validate(data)
    validate_script_references(script)
    return script
