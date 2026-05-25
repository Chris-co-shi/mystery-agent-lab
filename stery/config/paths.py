from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]

SCRIPTS_DIR = PROJECT_ROOT / "scripts"

ENV_FILE = PROJECT_ROOT / ".env"
RUNTIME_DIR = PROJECT_ROOT / "runtime"
SESSIONS_DIR = RUNTIME_DIR / "sessions"

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


def resolve_script_path(script_id: str) -> Path:
    """
    根据 script_id 解析剧本文件路径。

    示例：
    - script_id = "mansion_murder"
    - 返回 scripts/mansion_murder.json
    """
    return SCRIPTS_DIR / f"{script_id}.json"