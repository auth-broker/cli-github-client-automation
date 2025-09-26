from __future__ import annotations

import typer

from ...config.settings import get_settings
from .service import update_repos

app = typer.Typer(add_completion=False)


@app.command()
def update(
    dest: str = typer.Option(None, help="Destination directory"),
    mirror: bool = typer.Option(False, "--mirror", help="Treat repos as mirrors (bare)"),
):
    s = get_settings()
    update_repos(dest or s.default_dest, mirror)
