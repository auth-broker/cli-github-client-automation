"""Services for discarding local changes across repositories."""

from __future__ import annotations

import os

from ..core.git_client import GitClient
from ..core.utils import matches_any_glob


def _plan_repo_commands(
    *,
    git: GitClient,
    repo_dir: str,
    paths: list[str],
    mode: str,  # "hard" | "mixed" | "soft" (HEAD reset mode when paths not provided)
    clean_untracked: bool,
    clean_ignored: bool,
) -> list[list[str]]:
    """Build the list of git commands to execute for this repo.
    """
    cmds: list[list[str]] = []

    if paths:
        # Path-scoped discard using modern restore (affects index + worktree)
        cmds.append(["git", "restore", "--staged", "--worktree", *paths])
    else:
        # Reset entire repo to HEAD
        # mode usually "hard" for discarding changes; "mixed"/"soft" provided for flexibility.
        if mode not in {"hard", "mixed", "soft"}:
            mode = "hard"
        cmds.append(["git", "reset", f"--{mode}"])

    # Clean untracked/ignored if requested (order: reset/restore first, then clean)
    if clean_untracked or clean_ignored:
        flags = "-fdx" if clean_ignored else "-fd"
        cmds.append(["git", "clean", flags])

    return cmds


def discard_changes_batch(
    *,
    dest: str,
    paths: list[str],
    mode: str,  # "hard" | "mixed" | "soft"
    clean: bool,  # remove untracked files/dirs
    clean_ignored: bool,  # also remove ignored
    only_globs: list[str],
    exclude_globs: list[str],
    only_dirty: bool,  # skip repos with no changes
    dry_run: bool,
) -> None:
    git = GitClient()

    repos = git.find_worktrees(dest)
    if not repos:
        print("No repositories found.")
        return

    # Filter by folder name (basename)
    filtered: list[str] = []
    for d in repos:
        name = os.path.basename(d.rstrip(os.sep))
        if only_globs and not matches_any_glob(name, only_globs):
            continue
        if exclude_globs and matches_any_glob(name, exclude_globs):
            continue
        filtered.append(d)

    if not filtered:
        print("No repositories remain after filters.")
        return

    print(f"Discarding changes in {len(filtered)} repository(ies)...")
    ok = fail = skipped = 0

    for d in filtered:
        name = os.path.basename(d.rstrip(os.sep))

        if only_dirty and (not git.status_has_changes(d)):
            print(f"[skip] {name}: clean")
            skipped += 1
            continue

        cmds = _plan_repo_commands(
            git=git,
            repo_dir=d,
            paths=paths,
            mode=mode,
            clean_untracked=clean,
            clean_ignored=clean_ignored,
        )

        if dry_run:
            for c in cmds:
                print(f"[dry-run] {name}: {' '.join(c)}")
            ok += 1
            continue

        # Execute planned commands
        all_ok = True
        for c in cmds:
            success, err = git._run(c, cwd=d)  # uses GitClient's runner
            if not success:
                print(f"[fail] {name}: {' '.join(c)} -> {err}")
                all_ok = False
                break

        if all_ok:
            print(f"[ok] {name}")
            ok += 1
        else:
            fail += 1

    print(f"Done. ok={ok}, skipped={skipped}, failed={fail}.")
