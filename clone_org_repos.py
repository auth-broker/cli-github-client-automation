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

def pull_update(dest, mirror=False):
    # Optional helper: fetch/prune for existing clones
    git_dirs = []
    for root, dirs, files in os.walk(dest):
        if ".git" in dirs:
            git_dirs.append(root)
            dirs[:] = []  # don’t descend further
    if mirror:
        # mirrors end with .git and have no working tree
        for root, dirs, files in os.walk(dest):
            if root.endswith(".git") and os.path.isfile(os.path.join(root, "config")):
                git_dirs.append(root)
                dirs[:] = []
    git_dirs = sorted(set(git_dirs))
    ok = 0
    for d in git_dirs:
        cmd = ["git", "fetch", "--all", "--prune"]
        success, err = run(cmd, cwd=d)
        ok += 1 if success else 0
        if not success:
            print(f"[update fail] {d}: {err}", file=sys.stderr)
    return ok, len(git_dirs)

def main():
    ap = argparse.ArgumentParser(description="Clone all repos from a GitHub organisation.")
    ap.add_argument("--org", required=True, help="GitHub organisation login (e.g. 'pallets')")
    ap.add_argument("--token", default=os.getenv("GITHUB_TOKEN"), help="GitHub PAT (env GITHUB_TOKEN used if not set)")
    ap.add_argument("--dest", default="repos", help="Destination directory")
    ap.add_argument("--ssh", action="store_true", help="Use SSH URLs instead of HTTPS")
    ap.add_argument("--mirror", action="store_true", help="Use --mirror clones")
    ap.add_argument("--shallow", action="store_true", help="Use shallow clones (depth 1, single branch)")
    ap.add_argument("--include-archived", action="store_true", help="Include archived repositories")
    ap.add_argument("--visibility", choices=["all","public","private"], default="all",
                    help="Repo visibility filter (requires token for private)")
    ap.add_argument("--update", action="store_true", help="Fetch/prune existing clones instead of cloning")
    args = ap.parse_args()

    if not args.update and not args.token and args.visibility != "public":
        print("Warning: no token provided; only public repos will be visible.", file=sys.stderr)

    os.makedirs(args.dest, exist_ok=True)

    if args.update:
        ok, total = pull_update(args.dest, mirror=args.mirror)
        print(f"Updated {ok}/{total} existing clones.")
        return

    repos = list_org_repos(args.org, token=args.token, include_archived=args.include_archived,
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
