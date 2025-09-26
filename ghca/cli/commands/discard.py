"""CLI for discarding local changes across repositories."""

from __future__ import annotations

import typer

from ...config.settings import get_settings
from ...services.discard import discard_changes_batch

app = typer.Typer(add_completion=False)


@app.command()
def discard(
    dest: str | None = typer.Option(None, "--dest", help="Root folder of repositories"),
    path: list[str] = typer.Option(None, "--path", help="Path(s) to discard (repeatable). If omitted, whole repo."),
    mode: str = typer.Option("hard", "--mode", help="Reset mode if no --path given: hard|mixed|soft"),
    clean: bool = typer.Option(False, "--clean", help="Also remove untracked files/dirs (git clean -fd)"),
    clean_ignored: bool = typer.Option(False, "--clean-ignored", help="Also remove ignored files (git clean -fdx)"),
    only: str | None = typer.Option(None, "--only", help="Comma-separated repo name globs to include"),
    exclude: str | None = typer.Option(None, "--exclude", help="Comma-separated repo name globs to exclude"),
    all: bool = typer.Option(False, "--all", help="Do not skip clean repos (default skips clean)"),
    dry_run: bool = typer.Option(False, "--dry-run", help="Print actions without executing"),
):
    """Discard local changes across repositories.

    Examples:
      ghca discard --only 'service-*'                 # hard reset repos matching 'service-*'
      ghca discard --path 'package.json'              # restore a single file in each repo
      ghca discard --clean --clean-ignored            # also remove untracked & ignored files
      ghca discard --mode mixed                       # reset --mixed (keeps worktree changes)
      ghca discard --dry-run                          # preview actions

    """
    s = get_settings()
    discard_changes_batch(
        dest=dest or s.default_dest,
        paths=path or [],
        mode=mode.lower(),
        clean=clean,
        clean_ignored=clean_ignored,
        only_globs=(only.split(",") if only else []),
        exclude_globs=(exclude.split(",") if exclude else []),
        only_dirty=(not all),
        dry_run=dry_run,
    )
