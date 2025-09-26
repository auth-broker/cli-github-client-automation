from __future__ import annotations

import typer

from .commands.clone.cli import app as clone_app
from .commands.commit.cli import app as commit_app
from .commands.update.cli import app as update_app

app = typer.Typer(add_completion=False, help="Clone/update/commit/push across an org's GitHub repos.")

app.add_typer(clone_app, help="Clone all org repositories")
app.add_typer(update_app, help="Fetch/prune existing clones")
app.add_typer(commit_app, help="Batch commit & push across repos")
