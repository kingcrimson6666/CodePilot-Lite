"""App settings and framework bootstrapping."""

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
    """Prepare sys.path and load environment variables."""
    sys.path.insert(0, str(FRAMEWORK_ROOT))
    STORAGE_DIR.mkdir(parents=True, exist_ok=True)

    if load_dotenv:
        load_dotenv()
