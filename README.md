# ghca — quick commands

**Each item = what it does + copy-paste example.**

## clone — clone all org repos into a folder

```bash
uv run ghca clone --org auth-broker --dest ../ --visibility private --ssh
```

## update — fetch/prune all repos in a folder

```bash
uv run ghca update --dest ../
```

## commit — batch commit & push across repos

```bash
uv run ghca commit "chore: bump versions" --dest ../ --branch main
```

## release (auto) — per-repo `uv version` → tag `v<version>`, title `<version>`, generated notes, published

```bash
uv run ghca release --auto-from-uv --dest ../
```

## release (fixed) — create a specific tag across repos (with generated notes)

```bash
uv run ghca release --tag v0.3.0 --generate-notes --dest ../
```

## batch — run any command across folders

**Portable (recommended):**

```bash
uv run ghca batch --dest ../ -- uv version --bump patch
```

**Via shell (quoted string):**

```bash
uv run ghca batch --shell --dest ../ "uv version --bump patch"
```

## discard — discard local changes across repos

**Hard reset whole repo:**

```bash
uv run ghca discard --dest ../
```

**Specific paths only:**

```bash
uv run ghca discard --dest ../ --path package.json
```

**Also remove untracked/ignored files:**

```bash
uv run ghca discard --dest ../ --clean --clean-ignored
```
