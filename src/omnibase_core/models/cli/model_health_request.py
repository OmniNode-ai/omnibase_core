# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

from pydantic import BaseModel, ConfigDict, Field


class ModelHealthRequest(BaseModel):
    """The message-bus address the health command checks (OMN-26616)."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    kafka_bootstrap_servers: str | None = Field(
        default=None,
        description="The configured message-bus address; None when no address is set",
    )
