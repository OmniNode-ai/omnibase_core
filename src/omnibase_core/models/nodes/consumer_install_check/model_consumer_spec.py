# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""One downstream consumer a candidate build is installed into (OMN-26670)."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class ModelConsumerSpec(BaseModel):
    """A consumer repository, the ref checked out and how it is installed and collected.

    Every field comes from the overlay; the handler holds no consumer literal.
    """

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    name: str = Field(min_length=1, description="Consumer label shown in a failure")
    distribution: str = Field(
        min_length=1,
        description="Installed distribution whose entry points are imported",
    )
    repo_url: str = Field(min_length=1, description="Clone URL of the consumer")
    ref: str = Field(min_length=1, description="Branch, tag or sha checked out")
    install_args: tuple[str, ...] = Field(
        description="Arguments after 'uv pip install' that install the consumer and its test group"
    )
    collect_args: tuple[str, ...] = Field(
        description="Arguments after 'pytest --collect-only' naming the unit tests collected"
    )
    entry_point_groups: tuple[str, ...] = Field(
        default=(),
        description="Entry point groups imported; empty means every group of the distribution",
    )
    smoke_script: str = Field(
        default="",
        description="Consumer-owned stdlib smoke script, relative to its checkout, run by path after the entry-point import",
    )
