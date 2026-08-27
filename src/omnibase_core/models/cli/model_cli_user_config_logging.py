# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Logging settings declared in ``~/.onex/config.yaml``."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class ModelCliUserConfigLogging(BaseModel):
    """Local logging settings."""

    model_config = ConfigDict(
        extra="forbid",
        populate_by_name=True,
        from_attributes=True,
        frozen=True,
    )

    level: str = Field(default="INFO", description="Root log level")


__all__ = ["ModelCliUserConfigLogging"]
