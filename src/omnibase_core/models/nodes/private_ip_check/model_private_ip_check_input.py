# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Source text request for the private-IP COMPUTE validator."""

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.models.nodes.no_utcnow_check.model_source_file import ModelSourceFile


class ModelPrivateIpCheckInput(BaseModel):
    """Explicit source pairs; the handler never reads from disk."""

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)
    files: list[ModelSourceFile] = Field(default_factory=list)
