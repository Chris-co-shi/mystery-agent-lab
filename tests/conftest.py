from pathlib import Path

from dotenv import load_dotenv


def pytest_configure() -> None:
    """
    pytest 启动时自动加载项目根目录 .env。

    这样每个测试文件里都不用重复写 load_dotenv。
    """

    project_root = Path(__file__).resolve().parents[1]
    env_path = project_root / ".env"

    if env_path.exists():
        load_dotenv(env_path, override=False)
        return

    fallback_env_path = project_root / ".env"
    if fallback_env_path.exists():
        load_dotenv(fallback_env_path, override=False)