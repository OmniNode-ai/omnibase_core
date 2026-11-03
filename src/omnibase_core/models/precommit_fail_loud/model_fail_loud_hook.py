# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""A parsed hook for the fail-loud meta check (OMN-22357)."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, model_validator

__all__ = ["ModelFailLoudHook"]


class ModelFailLoudHook(BaseModel):
    """The hook fields the fail-loud rules read: id, entry, language, stages and args."""

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    id: str
    entry: str | None = None
    language: str | None = None
    stages: tuple[str, ...] = Field(default=())
    args: tuple[str, ...] = Field(default=())

    @model_validator(mode="before")
    @classmethod
    def _keep_read_keys(cls, data: object) -> object:
        """Drop the hook keys this view does not read; a hook carries many more."""
        if not isinstance(data, dict):
            return data
        kept: dict[str, object] = {
            key: data[key] for key in ("id", "entry", "language") if key in data
        }
        for key in ("stages", "args"):
            value = data.get(key) or []
            if not isinstance(value, list):
                raise ValueError(f"hook {data.get('id')!r}: {key} must be a list")
            kept[key] = [str(item) for item in value]
        return kept

    @property
    def command_lines(self) -> tuple[str, ...]:
        """The entry text, then each argument, as the lines a shell would read."""
        if self.entry is None:
            return ()
        return (self.entry, *self.args)
