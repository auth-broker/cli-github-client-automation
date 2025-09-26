from __future__ import annotations

import os

from dotenv import load_dotenv
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

# Load .env once, early
load_dotenv()


class Settings(BaseSettings):
    """Application config (env or .env)."""

    model_config = SettingsConfigDict(env_prefix="", env_file=None, extra="ignore")

    github_token: str | None = Field(default_factory=lambda: os.getenv("GITHUB_TOKEN"))
    default_dest: str = Field(default="repos")


def get_settings() -> Settings:
    # simple singleton pattern if you want; for now just construct
    return Settings()
