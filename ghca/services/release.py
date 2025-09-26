"""Service to batch-create GitHub Releases across repositories."""

from __future__ import annotations

import os
import re

from ..core.git_client import GitClient
from ..core.github_client import GitHubClient, GitHubError
from ..core.utils import matches_any_glob, resolve_asset_globs


_VERSION_RE = re.compile(r"(?P<version>\d+\.\d+\.\d+(?:[.-][0-9A-Za-z]+)*)")


def _derive_version_with_uv(git: GitClient, repo_dir: str) -> str | None:
    """
    Run `uv version` in repo_dir and return the parsed version string.
    Expected output format examples:
      - 'my-project 0.1.1'
      - '0.2.0'
    We'll take the last thing that looks like a semver-ish token.
    """
    ok, out = git._run_out(["uv", "version"], cwd=repo_dir)
    if not ok or not out:
        return None
    # pick the last semver-looking token in the output
    m = None
    for token in out.strip().split():
        mt = _VERSION_RE.fullmatch(token.strip())
        if mt:
            m = mt
    return m.group("version") if m else None


def batch_create_releases(
    *,
    dest: str,
    tag: str | None,                     # may be None in auto mode
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
    auto_from_uv: bool,                  # NEW: per-repo version discovery
    tag_prefix: str,                     # NEW: prefix for tag (default "v")
) -> None:
    git = GitClient()
    gh = GitHubClient(token=token)

    repos = git.find_worktrees(dest)
    if not repos:
        print("No repositories found.")
        return

    mode = "auto-from-uv" if auto_from_uv else f"fixed tag={tag}"
    print(f"Creating releases ({mode}) across {len(repos)} repositories...")
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

        # Optional guard: skip if no commits since last tag
        if since_last_tag_only:
            last = git.last_tag(d)
            if last and git.commits_since(d, last) == 0:
                print(f"[skip] {name}: no commits since last tag {last}")
                skipped += 1
                continue

        # Resolve assets
        asset_paths = resolve_asset_globs(d, assets)

        # Tag/title derivation
        eff_tag = tag
        eff_title = title

        if auto_from_uv:
            version = _derive_version_with_uv(git, d)
            if not version:
                print(f"[skip] {name}: could not derive version via `uv version`")
                skipped += 1
                continue
            eff_tag = f"{tag_prefix}{version}" if tag_prefix else version
            # title = version unless provided explicitly
            eff_title = eff_title or version
            # force auto notes / publish in auto mode unless user overrode
            eff_generate_notes = True if notes_file is None else generate_notes
            eff_draft = False
            eff_prerelease = False
        else:
            # fixed-tag mode; use user-provided switches as-is
            eff_generate_notes = generate_notes
            eff_draft = draft
            eff_prerelease = prerelease

        if not eff_tag:
            print(f"[skip] {name}: tag is empty")
            skipped += 1
            continue

        ok, msg = gh.create_release_with_gh(
            repo_full=repo_full,
            tag=eff_tag,
            title=eff_title,
            notes_file=notes_file,
            generate_notes=eff_generate_notes,
            draft=eff_draft,
            prerelease=eff_prerelease,
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
