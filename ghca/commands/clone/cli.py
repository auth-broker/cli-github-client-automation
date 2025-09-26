"""CLI for cloning repositories from an organisation."""

import typer

from ...config.settings import get_settings
from ...core.types import Visibility
from .service import clone_org

app = typer.Typer(add_completion=False)


@app.command()
def clone(
    org: str = typer.Option(..., help="GitHub organisation login (e.g. 'pallets')"),
    dest: str = typer.Option(None, help="Destination directory"),
    token: str | None = typer.Option(None, help="GitHub PAT"),
    ssh: bool = typer.Option(False, "--ssh", help="Use SSH URLs"),
    mirror: bool = typer.Option(False, "--mirror", help="Use --mirror clones"),
    shallow: bool = typer.Option(False, "--shallow", help="Shallow clones (depth 1)"),
    include_archived: bool = typer.Option(False, "--include-archived", help="Include archived repos"),
    visibility: Visibility = typer.Option(Visibility.all, case_sensitive=False),  # noqa: B008
):
    """Typer command to clone all repositories for an organisation."""
    s = get_settings()
    _dest = dest or s.default_dest
    _token = token if token is not None else s.github_token
    if visibility != Visibility.public and not _token:
        typer.echo("Warning: no token provided; only public repos will be visible.", err=True)

    clone_org(
        org=org,
        dest=_dest,
        token=_token,
        ssh=ssh,
        mirror=mirror,
        shallow=shallow,
        include_archived=include_archived,
        visibility=visibility.value,
    )
