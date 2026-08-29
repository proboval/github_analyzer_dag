import pandas as pd


def aggregate_by_language(repos: pd.DataFrame) -> pd.DataFrame:
    if repos.empty:
        return pd.DataFrame()
    cols = {
        "num_repos": (repos["full_name"], "count"),
        "total_stars": (repos["stars"], "sum"),
        "total_forks": (repos["forks"], "sum"),
        "avg_stars": (repos["stars"], "mean"),
        "avg_forks": (repos["forks"], "mean"),
        "avg_size_kb": (repos["size_kb"], "mean"),
    }
    out = pd.DataFrame(
        {name: repos.groupby("language")[col].agg(agg) for name, (col, agg) in cols.items()}
    )
    out = out.fillna(0).round(2).reset_index()
    out = out.sort_values("total_stars", ascending=False)
    return out


def aggregate_by_owner(repos: pd.DataFrame) -> pd.DataFrame:
    if repos.empty:
        return pd.DataFrame()
    out = (
        repos.groupby(["owner_login", "owner_type"])
        .agg(
            num_repos=("id", "count"),
            total_stars=("stars", "sum"),
            total_forks=("forks", "sum"),
            avg_stars=("stars", "mean"),
        )
        .round(2)
        .reset_index()
    )
    return out.sort_values("total_stars", ascending=False)


def aggregate_repo_activity(repos: pd.DataFrame, commits: pd.DataFrame) -> pd.DataFrame:
    if repos.empty:
        return pd.DataFrame()
    commit_count = (
        commits.groupby("repo_full_name").size().rename("recent_commits").reset_index()
    )
    out = repos.merge(
        commit_count, left_on="full_name", right_on="repo_full_name", how="left"
    )
    out["recent_commits"] = out["recent_commits"].fillna(0).astype(int)
    out["pushed_ago_days"] = (
        (pd.Timestamp.utcnow() - out["pushed_at"]).dt.days
        if out["pushed_at"].notna().any()
        else None
    )
    return out[
        ["full_name", "owner_login", "language", "stars", "forks", "recent_commits", "pushed_ago_days"]
    ].sort_values("recent_commits", ascending=False)


def aggregate_issue_stats(repos: pd.DataFrame, issues: pd.DataFrame) -> pd.DataFrame:
    if repos.empty:
        return pd.DataFrame()
    issue_count = (
        issues.groupby("repo_full_name").size().rename("open_issues").reset_index()
    )
    out = repos.merge(
        issue_count, left_on="full_name", right_on="repo_full_name", how="left"
    )
    out["open_issues"] = out["open_issues"].fillna(0).astype(int)
    return out[["full_name", "open_issues", "open_issues_count"]]
