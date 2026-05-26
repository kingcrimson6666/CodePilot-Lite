"""应用设置和框架引导"""

from pathlib import Path
import sys

try:
    from dotenv import load_dotenv
except ImportError:
    load_dotenv = None


REPO_ROOT = Path(__file__).resolve().parents[1]
FRAMEWORK_ROOT = REPO_ROOT / "frameworks" / "HelloAgents"
STORAGE_DIR = REPO_ROOT / "storage"


def init_environment() -> None:
    """准备 sys.path 并加载环境变量"""
    sys.path.insert(0, str(FRAMEWORK_ROOT))
    STORAGE_DIR.mkdir(parents=True, exist_ok=True)

    if load_dotenv:
        load_dotenv()
