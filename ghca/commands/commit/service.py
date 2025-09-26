"""Services for batch commit and push operations."""

from ...core.gitops import commit_and_push_one, find_git_worktrees


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
    repos = find_git_worktrees(dest)
    if not repos:
        print("No repositories found to commit/push.")
        return

    print(f"Batch committing to {len(repos)} repositories...")
    committed = pushed = skipped = failed = 0

    for d in repos:
        ok, msg = commit_and_push_one(
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
