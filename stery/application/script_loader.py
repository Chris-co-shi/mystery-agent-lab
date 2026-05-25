import json

from stery.application.script_validator import validate_script_references
from stery.config import resolve_script_path
from stery.domain.models import GameScript


def load_script(script_id: str ) -> GameScript:
    """
    加载剧本 JSON 文件。

    path 可以是：
    - 绝对路径
    - 相对项目根目录的路径，例如 scripts/mansion_murder.json
    """
    script_path = resolve_script_path(script_id)

    if not script_path.exists():
        raise FileNotFoundError(f"Script file not found: {script_path}")

    data = json.loads(script_path.read_text(encoding="utf-8"))

    script = GameScript.model_validate(data)
    validate_script_references(script)

    return script