# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""The inputs a removed-surface verdict was computed from."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class ModelGateInputsManifest(BaseModel):
    """Names every input of one gate run so the verdict is reproducible."""

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    repo: str = Field(min_length=1)
    base_sha: str = Field(min_length=1)
    head_sha: str = Field(min_length=1)
    graph_snapshot: str = Field(min_length=1)
    rules_sha256: str = Field(min_length=1)
