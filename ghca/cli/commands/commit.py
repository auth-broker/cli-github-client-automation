"""CLI for batch committing and pushing changes across repositories."""

from __future__ import annotations

import typer

from ...config.settings import get_settings
from ...services.commit import batch_commit_and_push

app = typer.Typer(add_completion=False)


@app.command()
def commit(
    message: str = typer.Argument(..., help="Commit message"),
    dest: str = typer.Option(None, help="Destination directory"),
    token: str | None = typer.Option(None, help="GitHub PAT"),
    branch: str | None = typer.Option(None, help="Branch to push to (default: current)"),
    allow_empty: bool = typer.Option(False, "--allow-empty", help="Allow empty commits"),
    sign: bool = typer.Option(False, "--sign", help="GPG-sign commits if configured"),
    no_verify: bool = typer.Option(False, "--no-verify", help="Skip push hooks"),
):
    """Typer command to run batch commit & push across repositories."""
    s = get_settings()
    _dest = dest or s.default_dest
    _token = token if token is not None else s.github_token

    batch_commit_and_push(
        dest=_dest,
        message=message,
        branch=branch,
        allow_empty=allow_empty,
        sign=sign,
        token=_token,
        push_no_verify=no_verify,
    )
