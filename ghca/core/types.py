"""Small types and Enums used by ghca."""

from enum import Enum


class Visibility(str, Enum):
    """Repository visibility options used by commands."""

    all = "all"
    public = "public"
    private = "private"
