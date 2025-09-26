#!/usr/bin/env python3
import argparse, json, os, subprocess, sys, time, urllib.request
from dotenv import load_dotenv
from urllib.parse import urlparse, urlunparse
load_dotenv()

API_BASE = "https://api.github.com"

def inject_token_into_https(clone_url: str, token: str) -> str:
    """
    Turn https://github.com/owner/repo.git into
    https://x-access-token:<token>@github.com/owner/repo.git
    """
    u = urlparse(clone_url)
    netloc = f"x-access-token:{token}@{u.netloc}"
    return urlunparse((u.scheme, netloc, u.path, u.params, u.query, u.fragment))

def gh_get(url, token=None):
    req = urllib.request.Request(url)
    req.add_header("Accept", "application/vnd.github+json")
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read().decode("utf-8"))

def list_org_repos(org, token=None, include_archived=False, visibility="all"):
    # visibility: all|public|private
    # type=all returns forks, sources, and mirrors
    repos = []
    page = 1
    per_page = 100
    while True:
        url = (f"{API_BASE}/orgs/{org}/repos"
               f"?per_page={per_page}&page={page}&type=all&sort=full_name&direction=asc&visibility={visibility}")
        data = gh_get(url, token)
        if not data:
            break
        for r in data:
            if (not include_archived) and r.get("archived"):
                continue
            repos.append(r)
        page += 1
    return repos

def run(cmd, cwd=None):
    try:
        subprocess.check_call(cmd, cwd=cwd)
        return True, None
    except subprocess.CalledProcessError as e:
        return False, f"{e}"

def run_out(cmd, cwd=None):
    """Run a command and return (success, stdout_str)."""
    try:
        out = subprocess.check_output(cmd, cwd=cwd, stderr=subprocess.STDOUT)
        return True, out.decode("utf-8").strip()
    except subprocess.CalledProcessError as e:
        return False, e.output.decode("utf-8", "ignore").strip()

def clone_repo(repo, dest, use_ssh=False, mirror=False, shallow=False, token=None):
    name = repo["name"]
    if use_ssh:
        url = repo["ssh_url"]
    else:
        url = repo["clone_url"]
        if token:
            url = inject_token_into_https(url, token)

    target = os.path.join(dest, name + (".git" if mirror else ""))
    if os.path.exists(target):
        return True, f"skip (exists): {name}"

    # disable interactive credential prompts so we fail fast if anything's wrong
    cmd = ["git", "-c", "credential.helper=", "clone"]
    if mirror:
        cmd.append("--mirror")
    elif shallow:
        cmd += ["--depth", "1", "--single-branch"]
    cmd += [url, target]
    return run(cmd)

def find_git_worktrees(dest):
    """Return a sorted list of *worktree* directories (skip bare/mirror .git dirs)."""
    worktrees = set()
    for root, dirs, files in os.walk(dest):
        if ".git" in dirs:
            worktrees.add(root)
            dirs[:] = []  # do not descend further
    # prune mirrors: they end with .git and have no working tree
    return sorted(d for d in worktrees if not d.endswith(".git"))

def pull_update(dest, mirror=False):
    # Optional helper: fetch/prune for existing clones
    git_dirs = []
    if mirror:
        for root, dirs, files in os.walk(dest):
            if root.endswith(".git") and os.path.isfile(os.path.join(root, "config")):
                git_dirs.append(root)
                dirs[:] = []
    else:
        git_dirs = find_git_worktrees(dest)

    ok = 0
    for d in sorted(set(git_dirs)):
        cmd = ["git", "fetch", "--all", "--prune"]
        success, err = run(cmd, cwd=d)
        ok += 1 if success else 0
        if not success:
            print(f"[update fail] {d}: {err}", file=sys.stderr)
    return ok, len(git_dirs)

def git_status_has_changes(repo_dir):
    success, out = run_out(["git", "status", "--porcelain"], cwd=repo_dir)
    if not success:
        return False
    return bool(out.strip())

def get_current_branch(repo_dir):
    ok, out = run_out(["git", "rev-parse", "--abbrev-ref", "HEAD"], cwd=repo_dir)
    if ok:
        return out.strip()
    return None

def get_origin_url(repo_dir):
    ok, out = run_out(["git", "remote", "get-url", "origin"], cwd=repo_dir)
    return out.strip() if ok else None

def batch_commit_and_push(dest, message, branch=None, allow_empty=False, sign=False, token=None, push_no_verify=False):
    """
    For each repo in `dest`:
      - stage all changes
      - commit with `message` (skip if no changes unless allow_empty)
      - push to origin <branch or current branch>
    """
    repos = find_git_worktrees(dest)
    if not repos:
        print("No repositories found to commit/push.")
        return

    print(f"Batch committing to {len(repos)} repositories...")
    committed = 0
    pushed = 0
    skipped_clean = 0
    failed = 0

    for d in repos:
        name = os.path.basename(d.rstrip(os.sep))
        # Ensure it's a git repo
        if not os.path.isdir(os.path.join(d, ".git")):
            print(f"[skip] {name}: not a git worktree")
            continue

        # Stage changes
        ok, err = run(["git", "add", "-A"], cwd=d)
        if not ok:
            print(f"[fail] {name}: git add failed: {err}", file=sys.stderr)
            failed += 1
            continue

        # Check if there is anything to commit
        dirty = git_status_has_changes(d)
        if not dirty and not allow_empty:
            print(f"[clean] {name}: no changes")
            skipped_clean += 1
            continue

        # Commit
        commit_cmd = ["git", "commit", "-m", message]
        if allow_empty:
            commit_cmd.append("--allow-empty")
        if sign:
            commit_cmd.append("-S")
        ok, err = run(commit_cmd, cwd=d)
        if not ok:
            # If commit fails due to nothing to commit (race), treat as clean
            if "nothing to commit" in (err or "").lower():
                print(f"[clean] {name}: nothing to commit")
                skipped_clean += 1
                continue
            print(f"[fail] {name}: git commit failed: {err}", file=sys.stderr)
            failed += 1
            continue
        committed += 1

        # Determine branch
        target_branch = branch or get_current_branch(d) or "main"

        # Build push command (avoid writing token to config)
        origin_url = get_origin_url(d)
        push_cmd = ["git", "push"]
        if push_no_verify:
            push_cmd.append("--no-verify")

        # If origin is HTTPS and token provided but not present in origin, inject for this push only
        push_url = None
        if origin_url and origin_url.startswith("https://") and token and "@" not in urlparse(origin_url).netloc:
            push_url = inject_token_into_https(origin_url, token)

        if push_url:
            push_cmd += [push_url, f"HEAD:{target_branch}"]
        else:
            push_cmd += ["-u", "origin", target_branch]

        ok, err = run(push_cmd, cwd=d)
        if ok:
            print(f"[pushed] {name} -> {target_branch}")
            pushed += 1
        else:
            print(f"[fail] {name}: git push failed: {err}", file=sys.stderr)
            failed += 1

    print(f"Done. committed={committed}, pushed={pushed}, clean={skipped_clean}, failed={failed}.")

def main():
    ap = argparse.ArgumentParser(description="Clone/update/commit/push all repos from a GitHub organisation.")
    sub = ap.add_subparsers(dest="cmd", required=False)

    # Global-ish flags
    ap.add_argument("--dest", default="repos", help="Destination directory")
    ap.add_argument("--token", default=os.getenv("GITHUB_TOKEN"), help="GitHub PAT (env GITHUB_TOKEN used if not set)")

    # clone subcommand
    sp_clone = sub.add_parser("clone", help="Clone all org repositories")
    sp_clone.add_argument("--org", required=True, help="GitHub organisation login (e.g. 'pallets')")
    sp_clone.add_argument("--ssh", action="store_true", help="Use SSH URLs instead of HTTPS")
    sp_clone.add_argument("--mirror", action="store_true", help="Use --mirror clones")
    sp_clone.add_argument("--shallow", action="store_true", help="Use shallow clones (depth 1, single branch)")
    sp_clone.add_argument("--include-archived", action="store_true", help="Include archived repositories")
    sp_clone.add_argument("--visibility", choices=["all","public","private"], default="all",
                         help="Repo visibility filter (requires token for private)")

    # update subcommand
    sp_update = sub.add_parser("update", help="Fetch/prune existing clones")
    sp_update.add_argument("--mirror", action="store_true", help="Treat repos as mirrors (bare)")

    # commit subcommand
    sp_commit = sub.add_parser("commit", help="Batch commit & push across repos")
    sp_commit.add_argument("-m", "--message", required=True, help="Commit message to use")
    sp_commit.add_argument("--branch", help="Branch to push to (default: current branch)")
    sp_commit.add_argument("--allow-empty", action="store_true", help="Allow empty commits")
    sp_commit.add_argument("--sign", action="store_true", help="GPG-sign commits if configured")
    sp_commit.add_argument("--no-verify", action="store_true", help="Skip hooks on push")

    # Back-compat flags (top-level) – if none provided, default to clone-like behaviour
    ap.add_argument("--org", help="(compat) GitHub org – used with legacy clone mode")
    ap.add_argument("--ssh", action="store_true", help="(compat) Use SSH URLs instead of HTTPS")
    ap.add_argument("--mirror", action="store_true", help="(compat) Use --mirror clones")
    ap.add_argument("--shallow", action="store_true", help="(compat) Use shallow clones")
    ap.add_argument("--include-archived", action="store_true", help="(compat) Include archived repositories")
    ap.add_argument("--visibility", choices=["all","public","private"], default="all",
                    help="(compat) Repo visibility filter")

    args = ap.parse_args()
    os.makedirs(args.dest, exist_ok=True)

    # Subcommand dispatch
    if args.cmd == "update":
        ok, total = pull_update(args.dest, mirror=getattr(args, "mirror", False))
        print(f"Updated {ok}/{total} existing clones.")
        return
    elif args.cmd == "commit":
        if not args.message:
            print("Commit message is required.", file=sys.stderr)
            sys.exit(2)
        batch_commit_and_push(
            dest=args.dest,
            message=args.message,
            branch=args.branch,
            allow_empty=args.allow_empty,
            sign=args.sign,
            token=args.token,
            push_no_verify=args.no_verify,
        )
        return
    else:
        # Default/clone
        if not args.org:
            print("Error: --org is required for clone mode. Or use subcommands: clone | update | commit.", file=sys.stderr)
            sys.exit(2)

        if (args.visibility != "public") and not args.token:
            print("Warning: no token provided; only public repos will be visible.", file=sys.stderr)

        repos = list_org_repos(args.org, token=args.token,
                               include_archived=args.include_archived,
                               visibility=args.visibility)
        if not repos:
            print("No repositories found (check org name / permissions).")
            return

        print(f"Found {len(repos)} repositories. Cloning to '{args.dest}'...")
        start = time.time()
        successes = 0
        for r in repos:
            success, msg = clone_repo(r, args.dest, use_ssh=args.ssh, mirror=args.mirror, shallow=args.shallow, token=args.token)
            name = r["full_name"]
            if success:
                print(f"[ok] {name} {('('+msg+')') if msg else ''}")
                successes += 1
            else:
                print(f"[fail] {name}: {msg}", file=sys.stderr)
        secs = time.time() - start
        print(f"Done. {successes}/{len(repos)} succeeded in {secs:.1f}s.")

if __name__ == "__main__":
    main()
