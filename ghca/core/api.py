from __future__ import annotations

import json
import urllib.request
from typing import Any
from urllib.parse import urlparse, urlunparse

from .constants import API_BASE, GITHUB_API_ACCEPT, HTTP_TIMEOUT_SEC, USER_AGENT


def inject_token_into_https(clone_url: str, token: str) -> str:
    """https://github.com/owner/repo.git -> https://x-access-token:<token>@github.com/owner/repo.git"""
    u = urlparse(clone_url)
    netloc = f"x-access-token:{token}@{u.netloc}"
    return urlunparse((u.scheme, netloc, u.path, u.params, u.query, u.fragment))


def gh_get(url: str, token: str | None = None) -> Any:
    req = urllib.request.Request(url)
    req.add_header("Accept", GITHUB_API_ACCEPT)
    req.add_header("User-Agent", USER_AGENT)
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    with urllib.request.urlopen(req, timeout=HTTP_TIMEOUT_SEC) as resp:
        return json.loads(resp.read().decode("utf-8"))


def list_org_repos(
    org: str,
    token: str | None = None,
    include_archived: bool = False,
    visibility: str = "all",
) -> list[dict[str, Any]]:
    repos: list[dict[str, Any]] = []
    page, per_page = 1, 100
    while True:
        url = (
            f"{API_BASE}/orgs/{org}/repos"
            f"?per_page={per_page}&page={page}&type=all&sort=full_name&direction=asc&visibility={visibility}"
        )
        data = gh_get(url, token)
        if not data:
            break
        for r in data:
            if (not include_archived) and r.get("archived"):
                continue
            repos.append(r)
        page += 1
    return repos
