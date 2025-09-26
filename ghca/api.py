import json
import urllib.request
from urllib.parse import urlparse, urlunparse
from typing import List, Dict, Any, Optional

API_BASE = "https://api.github.com"

def inject_token_into_https(clone_url: str, token: str) -> str:
    """https://github.com/owner/repo.git -> https://x-access-token:<token>@github.com/owner/repo.git"""
    u = urlparse(clone_url)
    netloc = f"x-access-token:{token}@{u.netloc}"
    return urlunparse((u.scheme, netloc, u.path, u.params, u.query, u.fragment))

def gh_get(url: str, token: Optional[str] = None) -> Any:
    req = urllib.request.Request(url)
    req.add_header("Accept", "application/vnd.github+json")
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read().decode("utf-8"))

def list_org_repos(
    org: str,
    token: Optional[str] = None,
    include_archived: bool = False,
    visibility: str = "all",
) -> List[Dict[str, Any]]:
    repos: List[Dict[str, Any]] = []
    page, per_page = 1, 100
    while True:
        url = (f"{API_BASE}/orgs/{org}/repos"
               f"?per_page={per_page}&page={page}&type=all&sort=full_name&direction=asc&visibility={visibility}")
        data = gh_get(url, token)
        if not data:
            break
        for r in data:
            if (not include_archived) and r.get("archived"):
                continue
            repos.append(r)
        page += 1
    return repos
