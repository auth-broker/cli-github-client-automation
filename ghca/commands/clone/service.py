"""Services for the clone command."""

import os
import sys
import time

from ...core.api import list_org_repos
from ...core.gitops import clone_repo


def clone_org(
    org: str,
    dest: str,
    token: str | None,
    ssh: bool,
    mirror: bool,
    shallow: bool,
    include_archived: bool,
    visibility: str,
) -> None:
    """Clone all repositories for an org into the destination directory."""
    os.makedirs(dest, exist_ok=True)
    repos = list_org_repos(org, token=token, include_archived=include_archived, visibility=visibility)
    if not repos:
        print("No repositories found (check org name / permissions).")
        return
    print(f"Found {len(repos)} repositories. Cloning to '{dest}'...")
    start = time.time()
    successes = 0
    for r in repos:
        ok, msg = clone_repo(r, dest, use_ssh=ssh, mirror=mirror, shallow=shallow, token=token)
        name = r["full_name"]
        if ok:
            print(f"[ok] {name} {('(' + msg + ')') if msg else ''}")
            successes += 1
        else:
            print(f"[fail] {name}: {msg}", file=sys.stderr)
    secs = time.time() - start
    print(f"Done. {successes}/{len(repos)} succeeded in {secs:.1f}s.")
