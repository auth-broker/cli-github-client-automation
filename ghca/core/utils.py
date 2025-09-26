"""Lightweight helpers for batch orchestration (globs, assets)."""
from __future__ import annotations

import fnmatch
import glob
import os
from typing import Sequence


def matches_any_glob(name: str, patterns: Sequence[str]) -> bool:
    if not patterns:
        return True  # no filters = match all
    return any(fnmatch.fnmatchcase(name, pat) for pat in patterns)


def resolve_asset_globs(repo_dir: str, patterns: Sequence[str]) -> list[str]:
    if not patterns:
        return []
    out: list[str] = []
    for p in patterns:
        out.extend(glob.glob(os.path.join(repo_dir, p)))
    return [p for p in out if os.path.isfile(p)]
