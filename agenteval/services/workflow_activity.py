"""Structured activity lines returned to Studio for preview/freeze transparency."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

ActivityLevel = Literal["info", "ok", "warn", "error"]


class WorkflowActivityEntry(BaseModel):
    model_config = ConfigDict(extra="forbid")

    ts: str = Field(description="UTC ISO-8601 timestamp")
    level: ActivityLevel = "info"
    message: str


class WorkflowActivityLog(BaseModel):
    model_config = ConfigDict(extra="forbid")

    entries: list[WorkflowActivityEntry] = Field(default_factory=list)

    def info(self, message: str) -> None:
        self._append("info", message)

    def ok(self, message: str) -> None:
        self._append("ok", message)

    def warn(self, message: str) -> None:
        self._append("warn", message)

    def error(self, message: str) -> None:
        self._append("error", message)

    def _append(self, level: ActivityLevel, message: str) -> None:
        self.entries.append(
            WorkflowActivityEntry(
                ts=datetime.now(UTC).isoformat(),
                level=level,
                message=message,
            )
        )
