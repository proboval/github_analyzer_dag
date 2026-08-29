import time

import requests

from .config import (
    GITHUB_API_BASE,
    GITHUB_TOKEN,
    MAX_COMMITS,
    MAX_ISSUES,
    MAX_PRS,
    PER_PAGE,
    USER_AGENT,
)


class GitHubClient:
    """Тонкий обёртка над GitHub REST API с обработкой rate limit."""

    def __init__(self, token: str = GITHUB_TOKEN):
        self.token = token
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": USER_AGENT})
        if token:
            self.session.headers.update({"Authorization": f"Bearer {token}"})

    def _get(self, url: str, params: dict | None = None) -> list | dict:
        for attempt in range(5):
            resp = self.session.get(url, params=params, timeout=30)
            if resp.status_code == 200:
                return resp.json()
            if resp.status_code in (403, 429):  # rate limit
                sleep = self._sleep_secs(resp)
                time.sleep(sleep)
                continue
            if resp.status_code == 404:
                return []
            resp.raise_for_status()
        raise RuntimeError(f"Rate limit exceeded for {url}")

    @staticmethod
    def _sleep_secs(resp: requests.Response) -> float:
        try:
            return max(float(resp.headers.get("Retry-After", 60)), 30)
        except ValueError:
            return 60

    def _paginate(self, url: str, per_page: int = PER_PAGE, limit: int = 50) -> list:
        items: list = []
        page = 1
        while len(items) < limit:
            batch = self._get(url, {"per_page": per_page, "page": page})
            if not batch:
                break
            items.extend(batch)
            if len(batch) < per_page:
                break
            page += 1
        return items[:limit]

    def top_repositories(self, n: int = 100) -> list[dict]:
        url = f"{GITHUB_API_BASE}/search/repositories"
        items: list[dict] = []
        q_pages = (n + PER_PAGE - 1) // PER_PAGE
        for page in range(1, q_pages + 1):
            data = self._get(
                url,
                {
                    "q": "stars:>1",
                    "sort": "stars",
                    "order": "desc",
                    "per_page": PER_PAGE,
                    "page": page,
                },
            )
            items.extend(data.get("items", []))
            if len(items) >= n:
                break
        return items[:n]

    def repo_commits(self, full_name: str, since: str | None = None) -> list[dict]:
        url = f"{GITHUB_API_BASE}/repos/{full_name}/commits"
        params = {} if not since else {"since": since}
        return self._paginate_with_params(url, params, MAX_COMMITS)

    def _paginate_with_params(self, url, params, limit):
        items = []
        page = 1
        while len(items) < limit:
            batch = self._get(url, {**params, "per_page": PER_PAGE, "page": page})
            if not batch:
                break
            items.extend(batch)
            if len(batch) < PER_PAGE:
                break
            page += 1
        return items[:limit]

    def repo_issues(self, full_name: str, state: str = "open") -> list[dict]:
        url = f"{GITHUB_API_BASE}/repos/{full_name}/issues"
        return self._paginate_with_params(url, {"state": state}, MAX_ISSUES)

    def repo_pulls(self, full_name: str, state: str = "open") -> list[dict]:
        url = f"{GITHUB_API_BASE}/repos/{full_name}/pulls"
        return self._paginate_with_params(url, {"state": state}, MAX_PRS)
