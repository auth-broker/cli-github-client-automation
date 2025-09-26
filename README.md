# Clone all org repositories

Tooling to clone every repository from the **auth-broker** GitHub organisation.

## Prerequisites

* Git
* Python 3.10+
* `uv` (for virtual env + deps): `pipx install uv` or `pip install uv`
* A GitHub **PAT** with org access (Contents: Read) — put it in `.env`

## Setup

1. Create `.env` in the project root:

```
GITHUB_TOKEN=ghp_your_token_here
```

2. Install deps (creates `.venv` automatically):

```bash
make sync
```

## Usage

Clone all private repos from **auth-broker** into the parent folder (`../`):

```bash
make clone
```

Update (fetch/prune) existing clones:

```bash
make update
```

## Notes

* The Makefile defaults to:

  * `ORG=auth-broker`
  * `DEST=../`
  * `--visibility private --ssh` (SSH cloning). Ensure your GitHub SSH key is configured.
    If you don’t use SSH, switch the default in the Makefile to HTTPS (PAT used from `.env`).
