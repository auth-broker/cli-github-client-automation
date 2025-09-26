"""CLI entrypoint that wires subcommands into a Typer app."""

import typer

from .commands.batch import app as batch_app
from .commands.clone import app as clone_app
from .commands.commit import app as commit_app
from .commands.discard import app as discard_app
from .commands.release import app as release_app

app = typer.Typer(add_completion=False, help="Clone/update/commit/push across an org's GitHub repos.")


app.add_typer(clone_app, help="Clone all org repositories")
app.add_typer(commit_app, help="Batch commit & push across repos")
app.add_typer(release_app, help="Release all repositories")
app.add_typer(batch_app, help="Batch commands across all repositories")
app.add_typer(discard_app, help="Discard local changes across all repositories")
