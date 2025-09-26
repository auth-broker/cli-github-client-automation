import os, subprocess, sys
from typing import List, Optional, Tuple
from .api import inject_token_into_https

def run(cmd: List[str], cwd: Optional[str] = None) -> Tuple[bool, Optional[str]]:
    try:
        subprocess.check_call(cmd, cwd=cwd)
        return True, None
    except subprocess.CalledProcessError as e:
        return False, f"{e}"

def run_out(cmd: List[str], cwd: Optional[str] = None) -> Tuple[bool, str]:
    try:
        out = subprocess.check_output(cmd, cwd=cwd, stderr=subprocess.STDOUT)
        return True, out.decode("utf-8").strip()
    except subprocess.CalledProcessError as e:
        return False, e.output.decode("utf-8", "ignore").strip()

def clone_repo(repo: dict, dest: str, use_ssh=False, mirror=False, shallow=False, token: Optional[str]=None):
    name = repo["name"]
    url = repo["ssh_url"] if use_ssh else repo["clone_url"]
    if (not use_ssh) and token:
        url = inject_token_into_https(url, token)

    target = os.path.join(dest, name + (".git" if mirror else ""))
    if os.path.exists(target):
        return True, f"skip (exists): {name}"

    cmd = ["git", "-c", "credential.helper=", "clone"]
    if mirror:
        cmd.append("--mirror")
    elif shallow:
        cmd += ["--depth", "1", "--single-branch"]
    cmd += [url, target]
    return run(cmd)

def find_git_worktrees(dest: str) -> List[str]:
    worktrees = set()
    for root, dirs, _ in os.walk(dest):
        if ".git" in dirs:
            worktrees.add(root)
            dirs[:] = []
    return sorted(d for d in worktrees if not d.endswith(".git"))

def pull_update(dest: str, mirror=False):
    git_dirs: List[str] = []
    if mirror:
        for root, dirs, files in os.walk(dest):
            if root.endswith(".git") and os.path.isfile(os.path.join(root, "config")):
                git_dirs.append(root)
                dirs[:] = []
    else:
        git_dirs = find_git_worktrees(dest)

    ok = 0
    for d in sorted(set(git_dirs)):
        success, err = run(["git", "fetch", "--all", "--prune"], cwd=d)
        ok += 1 if success else 0
        if not success:
            print(f"[update fail] {d}: {err}", file=sys.stderr)
    return ok, len(git_dirs)

def git_status_has_changes(repo_dir: str) -> bool:
    success, out = run_out(["git", "status", "--porcelain"], cwd=repo_dir)
    return bool(success and out.strip())

def get_current_branch(repo_dir: str) -> Optional[str]:
    ok, out = run_out(["git", "rev-parse", "--abbrev-ref", "HEAD"], cwd=repo_dir)
    return out.strip() if ok else None

def get_origin_url(repo_dir: str) -> Optional[str]:
    ok, out = run_out(["git", "remote", "get-url", "origin"], cwd=repo_dir)
    return out.strip() if ok else None

def batch_commit_and_push(
    dest: str,
    message: str,
    branch: Optional[str] = None,
    allow_empty: bool = False,
    sign: bool = False,
    token: Optional[str] = None,
    push_no_verify: bool = False,
):
    repos = find_git_worktrees(dest)
    if not repos:
        print("No repositories found to commit/push.")
        return

    print(f"Batch committing to {len(repos)} repositories...")
    committed = pushed = skipped_clean = failed = 0

    for d in repos:
        name = os.path.basename(d.rstrip(os.sep))
        if not os.path.isdir(os.path.join(d, ".git")):
            print(f"[skip] {name}: not a git worktree")
            continue

        ok, err = run(["git", "add", "-A"], cwd=d)
        if not ok:
            print(f"[fail] {name}: git add failed: {err}", file=sys.stderr); failed += 1; continue

        if not git_status_has_changes(d) and not allow_empty:
            print(f"[clean] {name}: no changes"); skipped_clean += 1; continue

        commit_cmd = ["git", "commit", "-m", message]
        if allow_empty: commit_cmd.append("--allow-empty")
        if sign:        commit_cmd.append("-S")
        ok, err = run(commit_cmd, cwd=d)
        if not ok:
            if err and "nothing to commit" in err.lower():
                print(f"[clean] {name}: nothing to commit"); skipped_clean += 1; continue
            print(f"[fail] {name}: git commit failed: {err}", file=sys.stderr); failed += 1; continue
        committed += 1

        target_branch = branch or get_current_branch(d) or "main"
        origin_url = get_origin_url(d)

        push_cmd = ["git", "push"]
        if push_no_verify: push_cmd.append("--no-verify")

        push_url = None
        if origin_url and origin_url.startswith("https://") and token:
            from urllib.parse import urlparse
            if "@" not in urlparse(origin_url).netloc:
                push_url = inject_token_into_https(origin_url, token)

        if push_url:
            push_cmd += [push_url, f"HEAD:{target_branch}"]
        else:
            push_cmd += ["-u", "origin", target_branch]

        ok, err = run(push_cmd, cwd=d)
        if ok:
            print(f"[pushed] {name} -> {target_branch}"); pushed += 1
        else:
            print(f"[fail] {name}: git push failed: {err}", file=sys.stderr); failed += 1

    print(f"Done. committed={committed}, pushed={pushed}, clean={skipped_clean}, failed={failed}.")
