from enum import Enum


class Visibility(str, Enum):
    all = "all"
    public = "public"
    private = "private"
