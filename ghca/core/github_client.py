"""GitHub API operations + gh-based release creation."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import urllib.request
from collections.abc import Sequence
from typing import Any
from urllib.parse import urlparse, urlunparse

from .constants import API_BASE, GITHUB_API_ACCEPT, HTTP_TIMEOUT_SEC, USER_AGENT


class GitHubError(RuntimeError):
    pass


class GitHubClient:
    def __init__(self, token: str | None = None) -> None:
        self.token = token

    # ---------- low-level HTTP ----------
    def _request_json(self, url: str) -> Any:
        req = urllib.request.Request(url)
        req.add_header("Accept", GITHUB_API_ACCEPT)
        req.add_header("User-Agent", USER_AGENT)
        if self.token:
            req.add_header("Authorization", f"Bearer {self.token}")
        with urllib.request.urlopen(req, timeout=HTTP_TIMEOUT_SEC) as resp:
            return json.loads(resp.read().decode("utf-8"))

    # ---------- public API ----------
    @staticmethod
    def inject_token_into_https(clone_url: str, token: str) -> str:
        """https://github.com/owner/repo.git -> https://x-access-token:<token>@github.com/owner/repo.git"""
        u = urlparse(clone_url)
        netloc = f"x-access-token:{token}@{u.netloc}"
        return urlunparse((u.scheme, netloc, u.path, u.params, u.query, u.fragment))

    def list_org_repos(
        self,
        org: str,
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
            data = self._request_json(url)
            if not data:
                break
            for r in data:
                if (not include_archived) and r.get("archived"):
                    continue
                repos.append(r)
            page += 1
        return repos

    # ---------- gh release backend ----------
    @staticmethod
    def _ensure_gh_available() -> None:
        if not shutil.which("gh"):
            raise GitHubError("GitHub CLI 'gh' not found. Install https://cli.github.com/ and run 'gh auth login'.")

    def create_release_with_gh(
        self,
        *,
        repo_full: str,  # "owner/name"
        tag: str,
        title: str | None = None,
        notes_file: str | None = None,
        generate_notes: bool = False,
        draft: bool = False,
        prerelease: bool = False,
        target: str | None = None,
        asset_paths: Sequence[str] = (),
        cwd: str | None = None,
        dry_run: bool = False,
    ) -> tuple[bool, str]:
        """Create a GitHub release via the gh CLI. Returns (ok, message)."""
        self._ensure_gh_available()

        cmd = ["gh", "release", "create", tag, "-R", repo_full, "--title", (title or tag)]
        if draft:
            cmd.append("--draft")
        if prerelease:
            cmd.append("--prerelease")
        if target:
            cmd += ["--target", target]
        if notes_file:
            cmd += ["--notes-file", notes_file]
        elif generate_notes:
            cmd.append("--generate-notes")
        for a in asset_paths:
            cmd += ["--assets", a]

        env = os.environ.copy()
        # allow token via env if not already present
        if self.token and "GITHUB_TOKEN" not in env and "GH_TOKEN" not in env:
            env["GITHUB_TOKEN"] = self.token

        if dry_run:
            return True, f"[dry-run] {' '.join(cmd)}"

        try:
            subprocess.check_call(cmd, cwd=cwd, env=env)
            return True, f"[released] {repo_full} tag={tag}"
        except subprocess.CalledProcessError as e:
            return False, f"gh failed: {e}"
