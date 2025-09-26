"""CLI for batch GitHub Releases."""

from __future__ import annotations

import typer

from ...config.settings import get_settings
from ...services.release import batch_create_releases

app = typer.Typer(add_completion=False)


@app.command()
def release(
    # Fixed-tag mode (optional if using auto)
    tag: str | None = typer.Option(
        None, "--tag", "-t", help="Release tag to create (e.g. v0.3.0). Omit if using --auto-from-uv."
    ),
    title: str | None = typer.Option(
        None, "--title", help="Release title (defaults to version in auto mode, else tag)"
    ),
    notes_file: str | None = typer.Option(None, "--notes-file", help="Path to release notes file"),
    generate_notes: bool = typer.Option(False, "--generate-notes", help="Use GitHub-generated notes (fixed-tag mode)"),
    draft: bool = typer.Option(False, "--draft", help="Create as draft (fixed-tag mode)"),
    prerelease: bool = typer.Option(False, "--prerelease", help="Mark as prerelease (fixed-tag mode)"),
    target: str | None = typer.Option(None, "--target", help="Target branch/SHA (default repo default)"),
    asset: list[str] = typer.Option(
        None, "--asset", help="Glob(s) of assets to upload; repeatable", show_default=False
    ),
    # Auto mode
    auto_from_uv: bool = typer.Option(
        False, "--auto-from-uv", help="Derive version via `uv version` per repo and release it"
    ),
    tag_prefix: str = typer.Option("", "--tag-prefix", help="Prefix for tag in auto mode ('' for none)"),
    # Batch/general
    dest: str | None = typer.Option(None, "--dest", help="Root folder of repos"),
    token: str | None = typer.Option(None, "--token", help="Override GH token if needed"),
    since_last_tag_only: bool = typer.Option(False, "--since-last-tag-only", help="Skip if no commits since last tag"),
    only: str | None = typer.Option(None, "--only", help="Comma-separated repo globs to include (e.g. 'ab-*,tool-*')"),
    exclude: str | None = typer.Option(None, "--exclude", help="Comma-separated repo globs to exclude"),
    dry_run: bool = typer.Option(False, "--dry-run", help="Print gh command without executing"),
):
    """Batch-create releases across repos.

    Examples:
      # Auto: read version from `uv version`, tag 'v<version>', title '<version>', generate notes, publish:
      ghca release --auto-from-uv --dest ../

      # Auto without 'v' prefix:
      ghca release --auto-from-uv --tag-prefix "" --dest ../

      # Fixed tag:
      ghca release --tag v0.3.0 --generate-notes --dest ../

    """
    s = get_settings()

    # Guard: require either fixed tag or auto mode
    if not auto_from_uv and not tag:
        raise typer.BadParameter("Provide --tag, or use --auto-from-uv.")

    batch_create_releases(
        dest=dest or s.default_dest,
        tag=tag,
        title=title,
        notes_file=notes_file,
        generate_notes=generate_notes,
        draft=draft,
        prerelease=prerelease,
        target=target,
        assets=asset or [],
        token=(token if token is not None else s.github_token),
        since_last_tag_only=since_last_tag_only,
        only_globs=(only.split(",") if only else []),
        exclude_globs=(exclude.split(",") if exclude else []),
        dry_run=dry_run,
        auto_from_uv=auto_from_uv,
        tag_prefix=tag_prefix,
    )
