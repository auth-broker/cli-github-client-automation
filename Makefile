# Usage:
#   make sync                         # install deps into .venv via uv
#   make clone ORG=my-org FLAGS="--visibility private --ssh"
#   make update DEST=repos

UV ?= uv
SCRIPT ?= clone_org_repos.py
ORG ?= auth-broker
DEST ?= ../
FLAGS ?=

# Ensure deps are installed (uses pyproject.toml)
sync:
	$(UV) sync

# Clone all org repos (uses the managed venv)
clone: sync
	$(UV) run $(SCRIPT) --org $(ORG) --dest $(DEST) $(FLAGS)

# Fetch/prune existing clones
update: sync
	$(UV) run $(SCRIPT) --update --dest $(DEST)

# Quick check that the token is visible to the runtime
env-check: sync
	$(UV) run python -c "from dotenv import load_dotenv; load_dotenv(); import os; print('GITHUB_TOKEN set:' , bool(os.getenv('GITHUB_TOKEN')))"
