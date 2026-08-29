"""Локальный запуск пайплайна без Docker (для теста).

Пример:
    python -m src.pipeline_run --top-n 5 --max-repos 3
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.config import ensure_dirs  # noqa: E402
from src.pipeline import extract_to_raw, transform_to_stage  # noqa: E402
from src.marts import (  # noqa: E402
    build_language_mart,
    build_organization_mart,
    build_player_mart,
)
from src.pipeline import _load  # noqa: E402


def run(top_n: int, max_repos: int, recent_days: int, token: str | None):
    ensure_dirs()
    print("== Extract ==")
    extract_to_raw(top_n=top_n, recent_days=recent_days, max_repos=max_repos, token=token)
    print("== Transform ==")
    transform_to_stage()

    repos = _load("repos_stage", __import__("src.config", fromlist=["STAGE_DIR"]).STAGE_DIR)
    commits = _load("commits_stage", __import__("src.config", fromlist=["STAGE_DIR"]).STAGE_DIR)
    issues = _load("issues_stage", __import__("src.config", fromlist=["STAGE_DIR"]).STAGE_DIR)
    pulls = _load("pulls_stage", __import__("src.config", fromlist=["STAGE_DIR"]).STAGE_DIR)

    print("== Marts ==")
    paths = build_player_mart(repos, commits, issues, pulls)
    paths["language_mart.parquet"] = build_language_mart(repos)
    paths["organization_mart.parquet"] = build_organization_mart(repos)
    for name, path in paths.items():
        print(f"  {name}: {path}")

    print("\nГотово! Витрины в data/marts/")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--top-n", type=int, default=100)
    parser.add_argument("--max-repos", type=int, default=20)
    parser.add_argument("--recent-days", type=int, default=30)
    parser.add_argument("--token", default=None)
    args = parser.parse_args()
    run(args.top_n, args.max_repos, args.recent_days, args.token)
