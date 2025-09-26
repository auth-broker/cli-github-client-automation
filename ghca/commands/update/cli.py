"""CLI for updating existing local repository clones."""

import typer

from ...config.settings import get_settings
from .service import update_repos

app = typer.Typer(add_completion=False)


@app.command()
def update(
    dest: str = typer.Option(None, help="Destination directory"),
    mirror: bool = typer.Option(False, "--mirror", help="Treat repos as mirrors (bare)"),
):
    """Typer command to update local clones under dest."""
    s = get_settings()
    update_repos(dest or s.default_dest, mirror)
