"""CLI: run an arbitrary command across folders under dest."""

from __future__ import annotations

from typing import List
import typer

from ...config.settings import get_settings
from ...services.batch import batch_run_command

app = typer.Typer(add_completion=False)


@app.command()
def batch(
    cmd: List[str] = typer.Argument(..., help="Command to run (and its args), e.g.: echo hello"),
    dest: str | None = typer.Option(None, "--dest", help="Root folder"),
    only_git: bool = typer.Option(False, "--only-git", help="Run only in git worktrees under dest"),
    recursive: bool = typer.Option(False, "--recursive", help="Recurse subfolders (ignored with --only-git)"),
    only: str | None = typer.Option(None, "--only", help="Comma-separated folder globs to include"),
    exclude: str | None = typer.Option(None, "--exclude", help="Comma-separated folder globs to exclude"),
    jobs: int = typer.Option(1, "--jobs", "-j", min=1, help="Parallel jobs"),
    fail_fast: bool = typer.Option(False, "--fail-fast", help="Stop after first failure"),
    dry_run: bool = typer.Option(False, "--dry-run", help="Print actions without executing"),
    shell: bool = typer.Option(False, "--shell", help="Run the command via the system shell"),
    env: List[str] = typer.Option(None, "--env", help="Extra env KEY=VAL (repeatable)"),
):
    """
    Run a command across folders in --dest.
    Examples:
      ghca batch -- ls -1
      ghca batch --only 'repo-*' -- echo running
      ghca batch --only-git --jobs 4 -- bash -lc 'git status -s'
    """
    s = get_settings()
    batch_run_command(
        dest=dest or s.default_dest,
        cmd=cmd,
        only_git=only_git,
        recursive=recursive,
        only_globs=(only.split(",") if only else []),
        exclude_globs=(exclude.split(",") if exclude else []),
        jobs=jobs,
        fail_fast=fail_fast,
        dry_run=dry_run,
        shell=shell,
        extra_env=env or [],
    )
