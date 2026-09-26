# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""Pinned chain topology contract version and digest."""

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.models.primitives.model_semver import ModelSemVer


class ModelExecutionGraphTopologyVersion(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    contract_version: ModelSemVer
    topology_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
