"""Service to batch-create GitHub Releases across repositories."""

from __future__ import annotations

import os

from ..core.git_client import GitClient
from ..core.github_client import GitHubClient, GitHubError
from ..core.utils import matches_any_glob, resolve_asset_globs


def batch_create_releases(
    *,
    dest: str,
    tag: str,
    title: str | None,
    notes_file: str | None,
    generate_notes: bool,
    draft: bool,
    prerelease: bool,
    target: str | None,
    assets: list[str],
    token: str | None,
    since_last_tag_only: bool,
    only_globs: list[str],
    exclude_globs: list[str],
    dry_run: bool,
) -> None:
    git = GitClient()
    gh = GitHubClient(token=token)

    repos = git.find_worktrees(dest)
    if not repos:
        print("No repositories found.")
        return

    print(f"Creating releases (tag={tag}) across {len(repos)} repositories...")
    released = skipped = failed = 0

    try:
        GitHubClient._ensure_gh_available()
    except GitHubError as e:
        print(f"Error: {e}")
        return

    for d in repos:
        name = os.path.basename(d.rstrip(os.sep))

        if only_globs and not matches_any_glob(name, only_globs):
            print(f"[skip] {name}: not in --only filter")
            continue
        if exclude_globs and matches_any_glob(name, exclude_globs):
            print(f"[skip] {name}: excluded by --exclude")
            continue

        origin = git.origin_url(d)
        repo_full = git.parse_repo_full_name(origin)
        if not repo_full:
            print(f"[skip] {name}: could not parse owner/repo from origin")
            skipped += 1
            continue

        if since_last_tag_only:
            last = git.last_tag(d)
            if last and git.commits_since(d, last) == 0:
                print(f"[skip] {name}: no commits since last tag {last}")
                skipped += 1
                continue

        asset_paths = resolve_asset_globs(d, assets)

        ok, msg = gh.create_release_with_gh(
            repo_full=repo_full,
            tag=tag,
            title=title,
            notes_file=notes_file,
            generate_notes=generate_notes,
            draft=draft,
            prerelease=prerelease,
            target=target,
            asset_paths=asset_paths,
            cwd=d,
            dry_run=dry_run,
        )
        print(msg)
        if ok:
            released += 1
        else:
            failed += 1

    print(f"Done. released={released}, skipped={skipped}, failed={failed}.")
