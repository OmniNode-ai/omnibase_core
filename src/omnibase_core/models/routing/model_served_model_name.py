# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Validated provider-local name of a model served by a router."""

from __future__ import annotations

from pydantic import ConfigDict, RootModel, field_validator


class ModelServedModelName(RootModel[str]):
    """Non-empty provider-local model name with a scalar JSON shape."""

    model_config = ConfigDict(frozen=True)

    @field_validator("root")
    @classmethod
    def _require_nonempty_name(cls, value: str) -> str:
        if not value.strip():
            msg = "served model name must be nonempty"
            raise ValueError(msg)
        return value


__all__ = ["ModelServedModelName"]
