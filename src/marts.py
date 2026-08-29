import pandas as pd

from .config import MARTS_DIR, ensure_dirs


def _write(df: pd.DataFrame, name: str) -> str:
    ensure_dirs()
    path = MARTS_DIR / f"{name}.parquet"
    df.to_parquet(path, index=False)
    return str(path)


def build_player_mart(
    repos: pd.DataFrame,
    commits: pd.DataFrame,
    issues: pd.DataFrame,
    pulls: pd.DataFrame,
) -> dict[str, str]:
    """Витрина со сводными метриками по каждому репозиторию."""
    if repos.empty:
        return {}

    commit_count = commits.groupby("repo_full_name").size().rename("recent_commits")
    issue_count = issues.groupby("repo_full_name").size().rename("open_issues")
    pr_count = pulls.groupby("repo_full_name").size().rename("open_prs")

    mart = repos.copy()
    mart = mart.merge(commit_count, left_on="full_name", right_index=True, how="left")
    mart = mart.merge(issue_count, left_on="full_name", right_index=True, how="left")
    mart = mart.merge(pr_count, left_on="full_name", right_index=True, how="left")

    for col in ["recent_commits", "open_issues", "open_prs"]:
        mart[col] = mart[col].fillna(0).astype(int)

    mart["days_since_push"] = round(
        (pd.Timestamp.utcnow() - mart["pushed_at"]).dt.days
    )
    mart = mart.sort_values("stars", ascending=False)

    columns = [
        "full_name",
        "owner_login",
        "language",
        "stars",
        "forks",
        "recent_commits",
        "open_issues",
        "open_prs",
        "days_since_push",
        "created_at",
        "license",
    ]
    return {"repo_mart.parquet": _write(mart[columns].head(200), "repo_mart")}


def build_language_mart(repos: pd.DataFrame) -> str:
    """Витрина агрегатов по языку программирования."""
    if repos.empty:
        return ""
    lang = (
        repos.groupby("language")
        .agg(
            num_repos=("full_name", "count"),
            total_stars=("stars", "sum"),
            total_forks=("forks", "sum"),
            avg_stars=("stars", "mean"),
        )
        .round(2)
        .sort_values("total_stars", ascending=False)
        .reset_index()
    )
    return _write(lang, "language_mart")


def build_organization_mart(repos: pd.DataFrame) -> str:
    """Витрина агрегатов по организациям/владельцам."""
    if repos.empty:
        return ""
    org = (
        repos.groupby(["owner_login", "owner_type"])
        .agg(
            num_repos=("full_name", "count"),
            total_stars=("stars", "sum"),
            total_forks=("forks", "sum"),
        )
        .round(2)
        .sort_values("total_stars", ascending=False)
        .reset_index()
    )
    return _write(org, "organization_mart")
