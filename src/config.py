import os
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = Path(os.getenv("GH_DATA_DIR", PROJECT_ROOT / "data"))
RAW_DIR = DATA_DIR / "raw"
STAGE_DIR = DATA_DIR / "stage"
MARTS_DIR = DATA_DIR / "marts"

# Значения из env с дефолтами (всегда переопределяются в Airflow через Variables/Connections)
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN", "")
TOP_N_REPOS = int(os.getenv("GH_TOP_N", "100"))
RECENT_DAYS = int(os.getenv("GH_RECENT_DAYS", "30"))

GITHUB_API_BASE = "https://api.github.com"
USER_AGENT = "github-analyzer-dag"

# Максимальные размеры выборок с GitHub API
PER_PAGE = 100
MAX_REPOS = 100
MAX_COMMITS = 100
MAX_ISSUES = 50
MAX_PRS = 50


def ensure_dirs() -> None:
    for d in (RAW_DIR, STAGE_DIR, MARTS_DIR):
        d.mkdir(parents=True, exist_ok=True)
