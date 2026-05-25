from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]

SCRIPTS_DIR = PROJECT_ROOT / "scripts"
MANSION_MURDER_SCRIPT = SCRIPTS_DIR / "mansion_murder.json"

ENV_FILE = PROJECT_ROOT / ".env"


def resolve_project_path(path: str | Path) -> Path:
    """
    将路径解析为项目内绝对路径。

    规则：
    - 绝对路径：原样返回
    - 相对路径：优先按项目根目录解析
    """
    target = Path(path)

    if target.is_absolute():
        return target

    return PROJECT_ROOT / target