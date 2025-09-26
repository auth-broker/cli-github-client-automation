"""Service: run an arbitrary command across folders under dest."""

from __future__ import annotations

import os
import shlex
import subprocess
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Iterable

from ..core.batch import matches_any_glob
from ..core.git_client import GitClient


def _list_target_dirs(dest: str, only_git: bool, recursive: bool) -> list[str]:
    if only_git:
        # Reuse existing discovery for git repos (non-bare worktrees).
        return GitClient().find_worktrees(dest)

    # Otherwise, use ordinary folders.
    targets: list[str] = []
    if recursive:
        for root, dirs, _files in os.walk(dest):
            # Don't include dest itself; only subdirs.
            if root == dest:
                # keep walking but don't add root
                for d in list(dirs):
                    if d.startswith(".git"):  # prune .git folders quickly
                        dirs.remove(d)
                continue
            targets.append(root)
            # prune .git dirs
            for d in list(dirs):
                if d == ".git":
                    dirs.remove(d)
    else:
        for name in os.listdir(dest):
            path = os.path.join(dest, name)
            if os.path.isdir(path):
                targets.append(path)
    return sorted(targets)


def _parse_env(env_kvs: list[str]) -> dict[str, str]:
    env: dict[str, str] = {}
    for kv in env_kvs:
        if "=" not in kv:
            raise ValueError(f"--env expects KEY=VAL, got: {kv!r}")
        k, v = kv.split("=", 1)
        env[k] = v
    return env


def _run_one(
    cwd: str,
    cmd: list[str],
    use_shell: bool,
    inherit_env: dict[str, str],
    dry_run: bool,
) -> tuple[str, bool, str]:
    name = os.path.basename(cwd.rstrip(os.sep))
    if dry_run:
        printable = " ".join(shlex.quote(c) for c in (["sh -c"] + [" ".join(cmd)] if use_shell else cmd))
        return name, True, f"[dry-run] {name}: {printable}"

    try:
        if use_shell:
            # Run via platform shell. Join a safe string for POSIX; on Windows, shell=True uses cmd.exe.
            proc = subprocess.run(" ".join(cmd), cwd=cwd, shell=True, env=inherit_env,
                                  capture_output=True, text=True)
        else:
            proc = subprocess.run(cmd, cwd=cwd, shell=False, env=inherit_env,
                                  capture_output=True, text=True)

        ok = (proc.returncode == 0)
        out = proc.stdout.strip()
        err = proc.stderr.strip()
        msg = f"[ok] {name}" if ok else f"[fail] {name} (exit {proc.returncode})"
        if out:
            msg += f"\n[out] {name}:\n{out}"
        if err:
            msg += f"\n[err] {name}:\n{err}"
        return name, ok, msg
    except Exception as e:
        return name, False, f"[fail] {name}: {e!r}"


def batch_run_command(
    *,
    dest: str,
    cmd: list[str],
    only_git: bool,
    recursive: bool,
    only_globs: list[str],
    exclude_globs: list[str],
    jobs: int,
    fail_fast: bool,
    dry_run: bool,
    shell: bool,
    extra_env: list[str],
) -> None:
    targets = _list_target_dirs(dest, only_git=only_git, recursive=recursive)
    if not targets:
        print("No target folders found.")
        return

    # Filter by globs against folder basename
    filtered: list[str] = []
    for d in targets:
        name = os.path.basename(d.rstrip(os.sep))
        if only_globs and not matches_any_glob(name, only_globs):
            continue
        if exclude_globs and matches_any_glob(name, exclude_globs):
            continue
        filtered.append(d)

    if not filtered:
        print("No target folders remain after filters.")
        return

    print(f"Running in {len(filtered)} folder(s) (jobs={jobs})...")
    ok_count = fail_count = 0

    # Prepare env for children
    base_env = os.environ.copy()
    if extra_env:
        base_env.update(_parse_env(extra_env))

    if jobs <= 1:
        for d in filtered:
            name, ok, msg = _run_one(d, cmd, shell, base_env, dry_run)
            print(msg)
            ok_count += 1 if ok else 0
            fail_count += 0 if ok else 1
            if fail_fast and not ok:
                break
    else:
        with ThreadPoolExecutor(max_workers=jobs) as pool:
            futures = {
                pool.submit(_run_one, d, cmd, shell, base_env, dry_run): d for d in filtered
            }
            for fut in as_completed(futures):
                name, ok, msg = fut.result()
                print(msg)
                ok_count += 1 if ok else 0
                fail_count += 0 if ok else 1
                if fail_fast and not ok:
                    # Best-effort: we can't cancel running tasks cleanly; just report and stop consuming.
                    break

    print(f"Done. ok={ok_count}, failed={fail_count}.")
