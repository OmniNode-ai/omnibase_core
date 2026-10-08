# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Typed serialized-artifact request at the write EFFECT boundary."""

from pydantic import BaseModel, ConfigDict


class ModelBoundaryImportArtifactWriteInput(BaseModel):
    """Write content already rendered by the pure analyzer."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    path: str
    content: str
