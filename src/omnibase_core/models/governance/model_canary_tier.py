# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""ModelCanaryTier — canary tier definition model — OMN-10250.

Ported from onex_change_control.canary.schema (Wave 3).
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, field_validator


class ModelCanaryTier(BaseModel):
    name: Literal["canary", "early_adopter", "ga"]
    repos: list[str]
    description: str

    @field_validator("repos")
    @classmethod
    def repos_not_empty(cls, v: list[str]) -> list[str]:
        if not v:
            msg = "repos list must not be empty"
            raise ValueError(msg)
        return v


__all__ = ["ModelCanaryTier"]
