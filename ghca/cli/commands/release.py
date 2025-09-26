"""CLI for batch GitHub Releases."""

from __future__ import annotations

import typer

from ...config.settings import get_settings
from ...services.release import batch_create_releases

app = typer.Typer(add_completion=False)


@app.command()
def release(
    tag: str = typer.Option(..., "--tag", "-t", help="Release tag to create (e.g. v0.3.0)"),
    title: str | None = typer.Option(None, "--title", help="Release title (defaults to tag)"),
    notes_file: str | None = typer.Option(None, "--notes-file", help="Path to release notes file"),
    generate_notes: bool = typer.Option(False, "--generate-notes", help="Use GitHub-generated notes"),
    draft: bool = typer.Option(False, "--draft", help="Create as draft"),
    prerelease: bool = typer.Option(False, "--prerelease", help="Mark as prerelease"),
    target: str | None = typer.Option(None, "--target", help="Target branch/SHA (default repo default)"),
    asset: list[str] = typer.Option(None, "--asset", help="Glob(s) of assets to upload; repeatable", show_default=False),
    dest: str | None = typer.Option(None, "--dest", help="Root folder of repos"),
    token: str | None = typer.Option(None, "--token", help="Override GH token if needed"),
    since_last_tag_only: bool = typer.Option(False, "--since-last-tag-only", help="Skip if no commits since last tag"),
    only: str | None = typer.Option(None, "--only", help="Comma-separated repo globs to include (e.g. 'ab-*,tool-*')"),
    exclude: str | None = typer.Option(None, "--exclude", help="Comma-separated repo globs to exclude"),
    dry_run: bool = typer.Option(False, "--dry-run", help="Print gh command without executing"),
):
    """Typer command to batch-create releases across repos."""
    s = get_settings()
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
    )
