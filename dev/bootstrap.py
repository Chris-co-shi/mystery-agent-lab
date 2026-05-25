from pathlib import Path
import sys


def bootstrap_project() -> None:
    """
    将项目根目录加入 sys.path。

    解决从 dev/ 目录直接运行脚本时，无法 import stery 的问题。
    """
    project_root = Path(__file__).resolve().parents[1]
    project_root_str = str(project_root)

    if project_root_str not in sys.path:
        sys.path.insert(0, project_root_str)