"""Services for batch commit and push operations."""

from __future__ import annotations

from ..core.git_client import GitClient


def batch_commit_and_push(
    dest: str,
    message: str,
    branch: str | None,
    allow_empty: bool,
    sign: bool,
    token: str | None,
    push_no_verify: bool,
) -> None:
    """Commit and push changes across repositories under dest."""
    git = GitClient()

    repos = git.find_worktrees(dest)
    if not repos:
        print("No repositories found to commit/push.")
        return

    print(f"Batch committing to {len(repos)} repositories...")
    committed = pushed = skipped = failed = 0

    for d in repos:
        ok, msg = git.commit_and_push_one(
            repo_dir=d,
            message=message,
            branch=branch,
            allow_empty=allow_empty,
            sign=sign,
            token=token,
            push_no_verify=push_no_verify,
        )
        print(msg)
        if ok:
            if msg.startswith("[clean]"):
                skipped += 1
            elif msg.startswith("[pushed]"):
                committed += 1
                pushed += 1
        else:
            failed += 1

    print(f"Done. committed={committed}, pushed={pushed}, clean={skipped}, failed={failed}.")
