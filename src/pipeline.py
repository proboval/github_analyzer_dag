import json

import pandas as pd

from .config import RAW_DIR, STAGE_DIR, ensure_dirs
from .extract import GitHubClient
from .transform import (
    transform_commits,
    transform_issues,
    transform_pulls,
    transform_repositories,
)


def _save_json(data, name: str, subdir) -> str:
    ensure_dirs()
    path = subdir / f"{name}.json"
    with open(path, "w") as f:
        json.dump(data, f, ensure_ascii=False, default=str)
    return str(path)


def _load_json(name: str, subdir):
    path = subdir / f"{name}.json"
    if not path.exists():
        return []
    with open(path) as f:
        return json.load(f)


def _save(df: pd.DataFrame, name: str, subdir) -> str:
    ensure_dirs()
    path = subdir / f"{name}.parquet"
    df.to_parquet(path, index=False)
    return str(path)


def _load(name: str, subdir) -> pd.DataFrame:
    path = subdir / f"{name}.parquet"
    if not path.exists():
        return pd.DataFrame()
    return pd.read_parquet(path)


def extract_to_raw(
    top_n: int = 100,
    recent_days: int = 30,
    token: str | None = None,
    max_repos: int = 20,
) -> dict[str, str]:
    client = GitHubClient(token or "")
    repos_raw = client.top_repositories(top_n)
    repos = repos_raw[:max_repos]

    full_names = [r["full_name"] for r in repos]
    since = None
    if recent_days:
        from datetime import datetime, timedelta, timezone

        since = (datetime.now(timezone.utc) - timedelta(days=recent_days)).isoformat()

    commits_by_repo = {name: client.repo_commits(name, since) for name in full_names}
    issues_by_repo = {name: client.repo_issues(name) for name in full_names}
    pulls_by_repo = {name: client.repo_pulls(name) for name in full_names}

    paths = {
        _save_json(repos_raw, "repos_raw", RAW_DIR): "repos_raw",
        _save_json(commits_by_repo, "commits_raw", RAW_DIR): "commits_raw",
        _save_json(issues_by_repo, "issues_raw", RAW_DIR): "issues_raw",
        _save_json(pulls_by_repo, "pulls_raw", RAW_DIR): "pulls_raw",
        _save_json(
            [
                {
                    "repo_full_name": name,
                    "commit_count": len(v),
                    "issue_count": len(issues_by_repo.get(name, [])),
                    "pr_count": len(pulls_by_repo.get(name, [])),
                }
                for name, v in commits_by_repo.items()
            ],
            "collected_meta",
            RAW_DIR,
        ): "collected_meta",
    }
    return {v: k for k, v in paths.items()}


def transform_to_stage() -> dict[str, str]:
    repos = _load_json("repos_raw", RAW_DIR)
    commits = _load_json("commits_raw", RAW_DIR)
    issues = _load_json("issues_raw", RAW_DIR)
    pulls = _load_json("pulls_raw", RAW_DIR)

    paths = {
        _save(transform_repositories(repos), "repos_stage", STAGE_DIR): "repos_stage",
        _save(transform_commits(commits), "commits_stage", STAGE_DIR): "commits_stage",
        _save(transform_issues(issues), "issues_stage", STAGE_DIR): "issues_stage",
        _save(transform_pulls(pulls), "pulls_stage", STAGE_DIR): "pulls_stage",
    }
    return paths
