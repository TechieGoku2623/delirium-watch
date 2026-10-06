"""Process configuration. No secrets are required for Phase 0."""

from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel, Field


class Settings(BaseModel):
    env: str = Field(default="dev")
    repo_root: Path = Field(default_factory=lambda: Path(__file__).resolve().parents[2])
    pretty_logs: bool = True

    @property
    def sample_dir(self) -> Path:
        return self.repo_root / "data" / "sample"

    @property
    def research_dir(self) -> Path:
        return self.repo_root / "research" / "phase0"


def get_settings() -> Settings:
    return Settings()
