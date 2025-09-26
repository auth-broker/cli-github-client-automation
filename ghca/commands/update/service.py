from __future__ import annotations

import os

from ...core.gitops import pull_update


def update_repos(dest: str, mirror: bool) -> None:
    os.makedirs(dest, exist_ok=True)
    ok, total = pull_update(dest, mirror=mirror)
    print(f"Updated {ok}/{total} existing clones.")
