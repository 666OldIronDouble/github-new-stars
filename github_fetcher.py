import base64
from dataclasses import dataclass

import httpx

from config import GITHUB_TOKEN


@dataclass
class RepoInfo:
    name: str
    url: str
    stars: int
    language: str
    description: str


def _headers() -> dict[str, str]:
    headers = {"Accept": "application/vnd.github+json"}
    if GITHUB_TOKEN:
        headers["Authorization"] = f"Bearer {GITHUB_TOKEN}"
    return headers


def fetch_trending_repos(top_n: int = 10) -> list[RepoInfo]:
    """获取一周内 star 增长最快的 GitHub 项目。

    策略：
    1. 最近一周创建的新项目（按 star 降序）—— 反映当下热门趋势
    2. 最近两周创建的项目（补充更多近期增长项目）
    不再混入老牌高 star 项目，确保结果反映"趋势"而非"历史"。
    """
    from datetime import datetime, timedelta

    one_week_ago = (datetime.utcnow() - timedelta(weeks=1)).strftime("%Y-%m-%d")
    two_weeks_ago = (datetime.utcnow() - timedelta(weeks=2)).strftime("%Y-%m-%d")

    seen: set[str] = set()
    repos: list[RepoInfo] = []

    # 策略1：一周内创建的热门新项目
    new_query = f"created:>{one_week_ago} stars:>10"
    _fetch_page(new_query, top_n, seen, repos)

    # 策略2：两周内创建的热门项目（补充更多结果）
    if len(repos) < top_n:
        growth_query = f"created:>{two_weeks_ago} stars:>50"
        _fetch_page(growth_query, top_n, seen, repos)

    # 按 star 降序排序，取 top_n
    repos.sort(key=lambda r: r.stars, reverse=True)
    return repos[:top_n]


def _fetch_page(
    query: str, per_page: int, seen: set[str], repos: list[RepoInfo]
) -> None:
    """执行一次 GitHub Search API 请求，将结果追加到 repos 列表。"""
    url = "https://api.github.com/search/repositories"
    params = {
        "q": query,
        "sort": "stars",
        "order": "desc",
        "per_page": per_page,
    }

    try:
        with httpx.Client(headers=_headers(), timeout=30) as client:
            resp = client.get(url, params=params)
            if resp.status_code == 403:
                print("  [警告] GitHub API 速率限制，跳过此查询。")
                return
            resp.raise_for_status()
            data = resp.json()
    except httpx.HTTPError as e:
        print(f"  [警告] GitHub API 请求失败: {e}")
        return

    for item in data.get("items", []):
        full_name = item["full_name"]
        if full_name in seen:
            continue
        seen.add(full_name)
        repos.append(
            RepoInfo(
                name=full_name,
                url=item["html_url"],
                stars=item["stargazers_count"],
                language=item.get("language") or "N/A",
                description=item.get("description") or "",
            )
        )


def fetch_readme(repo_full_name: str) -> str:
    """获取仓库的 README 文本内容，失败返回空字符串。"""
    url = f"https://api.github.com/repos/{repo_full_name}/readme"
    try:
        with httpx.Client(headers=_headers(), timeout=30) as client:
            resp = client.get(url)
            if resp.status_code != 200:
                return ""
            data = resp.json()
            content = data.get("content", "")
            return base64.b64decode(content).decode("utf-8", errors="replace")
    except Exception:
        return ""
