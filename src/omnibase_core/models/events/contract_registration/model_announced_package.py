# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""The installed package an announcement came from (OMN-21589)."""

from pydantic import BaseModel, ConfigDict, Field


class ModelAnnouncedPackage(BaseModel):
    """Distribution name and exact installed version, read from installed metadata."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    distribution: str = Field(min_length=1, description="Installed distribution name")
    version: str = Field(min_length=1, description="Exact installed version")
