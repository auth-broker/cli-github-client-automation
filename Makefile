# Usage:
#   make sync                         # install deps into .venv via uv
#   make clone ORG=my-org FLAGS="--visibility private --ssh"
#   make update DEST=repos

UV ?= uv
SCRIPT ?= main.py
ORG ?= auth-broker
DEST ?= ../
FLAGS ?=

# Ensure deps are installed (uses pyproject.toml)
sync:
	$(UV) sync

# Quick check that the token is visible to the runtime
env-check: sync
	$(UV) run python -c "from dotenv import load_dotenv; load_dotenv(); import os; print('GITHUB_TOKEN set:' , bool(os.getenv('GITHUB_TOKEN')))"

# Clone all org repos (uses the managed venv)
clone: sync
	$(UV) run $(SCRIPT) --org $(ORG) --dest $(DEST) $(FLAGS)

# Fetch/prune existing clones
update: sync
	$(UV) run $(SCRIPT) --update --dest $(DEST)

# Batch commit & push across all repos in DEST
# Usage:
#   make commit MSG="chore: bump lockfiles" BRANCH=main
commit: sync
	$(UV) run $(SCRIPT) commit -m "$(MSG)" --dest $(DEST) $(if $(BRANCH),--branch $(BRANCH),)

# Optional: skip hooks or allow empty
#   make commit MSG="ci: trigger" FLAGS="--allow-empty --no-verify"
commit-flags: sync
	$(UV) run $(SCRIPT) commit -m "$(MSG)" --dest $(DEST) $(FLAGS)
