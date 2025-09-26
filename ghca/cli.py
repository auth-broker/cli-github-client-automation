import os

import typer
from dotenv import load_dotenv

from .api import list_org_repos
from .gitops import (
    batch_commit_and_push,
    clone_repo,
    pull_update,
)
from .types import Visibility

app = typer.Typer(add_completion=False, help="Clone/update/commit/push across an org's GitHub repos.")
load_dotenv()  # allow .env GITHUB_TOKEN etc.


def _default_token():
    return os.getenv("GITHUB_TOKEN")


@app.command()
def clone(
    org: str = typer.Option(..., help="GitHub organisation login (e.g. 'pallets')"),
    dest: str = typer.Option("repos", help="Destination directory"),
    token: str | None = typer.Option(_default_token(), help="GitHub PAT"),
    ssh: bool = typer.Option(False, "--ssh", help="Use SSH URLs"),
    mirror: bool = typer.Option(False, "--mirror", help="Use --mirror clones"),
    shallow: bool = typer.Option(False, "--shallow", help="Shallow clones (depth 1)"),
    include_archived: bool = typer.Option(False, "--include-archived", help="Include archived repos"),
    visibility: Visibility = typer.Option(Visibility.all, case_sensitive=False),
):
    os.makedirs(dest, exist_ok=True)
    if visibility != Visibility.public and not token:
        typer.echo("Warning: no token provided; only public repos will be visible.", err=True)

    repos = list_org_repos(org, token=token, include_archived=include_archived, visibility=visibility.value)
    if not repos:
        typer.echo("No repositories found (check org name / permissions).")
        raise typer.Exit(code=0)

    typer.echo(f"Found {len(repos)} repositories. Cloning to '{dest}'...")
    successes = 0
    for r in repos:
        ok, msg = clone_repo(r, dest, use_ssh=ssh, mirror=mirror, shallow=shallow, token=token)
        name = r["full_name"]
        if ok:
            typer.echo(f"[ok] {name} {('(' + msg + ')') if msg else ''}")
            successes += 1
        else:
            typer.secho(f"[fail] {name}: {msg}", err=True)
    typer.echo(f"Done. {successes}/{len(repos)} succeeded.")


@app.command()
def update(
    dest: str = typer.Option("repos", help="Destination directory"),
    mirror: bool = typer.Option(False, "--mirror", help="Treat repos as mirrors (bare)"),
):
    os.makedirs(dest, exist_ok=True)
    ok, total = pull_update(dest, mirror=mirror)
    typer.echo(f"Updated {ok}/{total} existing clones.")


@app.command()
def commit(
    message: str = typer.Argument(..., help="Commit message"),
    dest: str = typer.Option("repos", help="Destination directory"),
    token: str | None = typer.Option(_default_token(), help="GitHub PAT"),
    branch: str | None = typer.Option(None, help="Branch to push to (default: current)"),
    allow_empty: bool = typer.Option(False, "--allow-empty", help="Allow empty commits"),
    sign: bool = typer.Option(False, "--sign", help="GPG-sign commits if configured"),
    no_verify: bool = typer.Option(False, "--no-verify", help="Skip push hooks"),
):
    os.makedirs(dest, exist_ok=True)
    batch_commit_and_push(
        dest=dest,
        message=message,
        branch=branch,
        allow_empty=allow_empty,
        sign=sign,
        token=token,
        push_no_verify=no_verify,
    )
