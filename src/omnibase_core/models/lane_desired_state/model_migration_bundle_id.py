# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class ModelMigrationBundleId(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    bundle_name: Literal["omnibase-infra-migrate", "omninode-cloud-migrate"] = Field(
        ..., description="Migration bundle name"
    )
    image_digest: str = Field(
        ...,
        description="Immutable image digest",
        pattern=r"^sha256:[0-9a-f]{64}$",
    )
    built_for_head_sha: str = Field(
        ...,
        description="Git head SHA the bundle was built for",
        pattern=r"^[0-9a-f]{40}$",
    )


__all__ = ["ModelMigrationBundleId"]
