"""The single failure type. Every failure says what to do next (ADR-0001)."""

from __future__ import annotations

from typing import Any


class ToolError(Exception):
    """A contract failure. The CLI renders it to stderr and exits 1 (ADR-0006)."""

    def __init__(self, error: str, detail: dict[str, Any], next_step: str) -> None:
        super().__init__(error)
        self.error = error
        self.detail = detail
        self.next_step = next_step

    def to_dict(self) -> dict[str, Any]:
        return {"error": self.error, "detail": self.detail, "next": self.next_step}
