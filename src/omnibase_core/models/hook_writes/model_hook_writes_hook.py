# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""A parsed hook for the hook-writes check (OMN-21433)."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, model_validator

__all__ = ["ModelHookWritesHook"]


class ModelHookWritesHook(BaseModel):
    """The hook id and command fields relevant to judging file writes."""

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    id: str
    entry: str | None = None
    args: tuple[str, ...] = Field(default=())

    @model_validator(mode="before")
    @classmethod
    def _keep_read_keys(cls, data: object) -> object:
        """Drop the hook keys this view does not read; a hook carries many more."""
        if not isinstance(data, dict):
            return data
        kept = {key: data[key] for key in ("id", "entry") if key in data}
        args = data.get("args", [])
        if not isinstance(args, list):
            raise ValueError(f"hook {data.get('id')!r}: args must be a list")
        kept["args"] = [str(arg) for arg in args]
        return kept

    @property
    def command(self) -> str:
        """Join the entry, when present, and arguments in command order."""
        parts = self.args if self.entry is None else (self.entry, *self.args)
        return " ".join(parts)
