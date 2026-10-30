# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Uninterpreted package identity from uv.lock."""

from pydantic import BaseModel, ConfigDict


class ModelDevTagLineageLockEntry(BaseModel):
    """An adjacent lockfile may have zero, one or several entries per package."""

    model_config = ConfigDict(frozen=True, extra="forbid")
    package: str
    version: str
    git: str
