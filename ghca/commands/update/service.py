from __future__ import annotations

"""Service helpers for updating repository clones."""

import os

from ...core.gitops import pull_update


def update_repos(dest: str, mirror: bool) -> None:
    """Ensure dest exists and pull updates for repositories under it."""
    os.makedirs(dest, exist_ok=True)
    ok, total = pull_update(dest, mirror=mirror)
    print(f"Updated {ok}/{total} existing clones.")
