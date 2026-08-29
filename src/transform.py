from datetime import datetime, timezone

import pandas as pd


def _to_iso(value) -> str | None:
    if not value:
        return None
    if isinstance(value, str):
        return value
    if isinstance(value, (datetime,)):
        return value.isoformat()
    return str(value)


def _author_login(author: dict | None, committer: dict | None) -> str:
    if isinstance(author, dict) and author.get("login"):
        return author["login"]
    if isinstance(committer, dict) and committer.get("login"):
        return committer["login"]
    return "unknown"


def transform_repositories(raw: list[dict]) -> pd.DataFrame:
    records = []
    for r in raw:
        owner = r.get("owner") or {}
        records.append(
            {
                "id": r.get("id"),
                "full_name": r.get("full_name"),
                "name": r.get("name"),
                "owner_login": owner.get("login"),
                "owner_type": owner.get("type"),
                "description": r.get("description"),
                "html_url": r.get("html_url"),
                "language": r.get("language"),
                "stars": r.get("stargazers_count", 0),
                "forks": r.get("forks_count", 0),
                "open_issues_count": r.get("open_issues_count", 0),
                "watchers": r.get("watchers_count", 0),
                "size_kb": r.get("size", 0),
                "license": (r.get("license") or {}).get("spdx_id"),
                "created_at": _to_iso(r.get("created_at")),
                "updated_at": _to_iso(r.get("updated_at")),
                "pushed_at": _to_iso(r.get("pushed_at")),
                "is_fork": r.get("fork", False),
                "has_issues": r.get("has_issues", False),
                "topics": ",".join(r.get("topics") or []),
            }
        )
    df = pd.DataFrame(records)
    if not df.empty:
        df = df.drop_duplicates(subset="id")
        for col in ["stars", "forks", "open_issues_count", "watchers", "size_kb"]:
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0).astype(int)
        for col in ["created_at", "updated_at", "pushed_at"]:
            df[col] = pd.to_datetime(df[col], errors="coerce", utc=True)
    return df


def transform_commits(raw_by_repo: dict[str, list[dict]], recent_days: int = 30) -> pd.DataFrame:
    cutoff = datetime.now(timezone.utc).timestamp() - recent_days * 86400
    records = []
    for full_name, commits in raw_by_repo.items():
        for c in commits:
            commit = c.get("commit") or {}
            author = c.get("author")
            committer = c.get("committer")
            try:
                ts = datetime.fromisoformat(
                    (commit.get("author") or {}).get("date", "").replace("Z", "+00:00")
                ).timestamp()
            except (ValueError, TypeError):
                ts = 0.0
            if ts < cutoff:
                continue
            records.append(
                {
                    "repo_full_name": full_name,
                    "sha": c.get("sha"),
                    "message": (commit.get("message") or "")[:500],
                    "author_login": _author_login(author, committer),
                    "committed_at": _to_iso(commit.get("committer", {}).get("date")),
                }
            )
    df = pd.DataFrame(records)
    if not df.empty:
        df = df.drop_duplicates(subset=["repo_full_name", "sha"])
        df["committed_at"] = pd.to_datetime(df["committed_at"], errors="coerce", utc=True)
    return df


def transform_issues(raw_by_repo: dict[str, list[dict]]) -> pd.DataFrame:
    records = []
    for full_name, issues in raw_by_repo.items():
        for i in issues:
            user = i.get("user") or {}
            records.append(
                {
                    "repo_full_name": full_name,
                    "issue_id": i.get("id"),
                    "number": i.get("number"),
                    "title": i.get("title"),
                    "state": i.get("state"),
                    "user_login": user.get("login"),
                    "created_at": _to_iso(i.get("created_at")),
                    "closed_at": _to_iso(i.get("closed_at")),
                    "labels": ",".join(l.get("name", "") for l in i.get("labels") or []),
                    "comments": i.get("comments", 0),
                }
            )
    df = pd.DataFrame(records)
    if not df.empty:
        df = df.drop_duplicates(subset=["repo_full_name", "issue_id"])
        for col in ["created_at", "closed_at"]:
            df[col] = pd.to_datetime(df[col], errors="coerce", utc=True)
    return df


def transform_pulls(raw_by_repo: dict[str, list[dict]]) -> pd.DataFrame:
    records = []
    for full_name, pulls in raw_by_repo.items():
        for p in pulls:
            user = p.get("user") or {}
            records.append(
                {
                    "repo_full_name": full_name,
                    "pr_id": p.get("id"),
                    "number": p.get("number"),
                    "title": p.get("title"),
                    "state": p.get("state"),
                    "user_login": user.get("login"),
                    "additions": p.get("additions", 0),
                    "deletions": p.get("deletions", 0),
                    "changed_files": p.get("changed_files", 0),
                    "created_at": _to_iso(p.get("created_at")),
                    "closed_at": _to_iso(p.get("closed_at")),
                    "merged_at": _to_iso(p.get("merged_at")),
                }
            )
    df = pd.DataFrame(records)
    if not df.empty:
        df = df.drop_duplicates(subset=["repo_full_name", "pr_id"])
        for col in ["created_at", "closed_at", "merged_at"]:
            df[col] = pd.to_datetime(df[col], errors="coerce", utc=True)
    return df
