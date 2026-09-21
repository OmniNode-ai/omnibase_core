# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Typed schema for the governed runtime-ops verb allowlist."""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, StrictStr, field_validator


class ModelRuntimeOpsVerbAllowlist(BaseModel):
    """Non-empty mutation verb set loaded from the bundled contract YAML."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    schema_version: Literal[1]
    runtime_ops_verbs: tuple[StrictStr, ...] = Field(min_length=1)

    @field_validator("runtime_ops_verbs")
    @classmethod
    def validate_verbs(cls, verbs: tuple[StrictStr, ...]) -> tuple[str, ...]:
        normalized = tuple(verb.strip() for verb in verbs)
        if any(not verb for verb in normalized):
            raise ValueError("runtime_ops_verbs entries must be non-blank strings")
        return normalized


__all__ = ["ModelRuntimeOpsVerbAllowlist"]
