# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Inline source and hash-only denylist input for the pure validator."""

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.models.nodes.no_utcnow_check.model_source_file import ModelSourceFile


class ModelExposedIdentifiersCheckInput(BaseModel):
    """Sources selected by the caller and the caller-supplied JSON document."""

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)
    files: list[ModelSourceFile] = Field(default_factory=list)
    denylist_json: str
