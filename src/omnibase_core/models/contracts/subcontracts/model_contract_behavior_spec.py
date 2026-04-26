# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

from pydantic import BaseModel, ConfigDict, Field


class ModelContractBehaviorSpec(BaseModel):
    """Behavioral execution profile extracted from ModelContractBase (first slice)."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    max_concurrency: int | None = Field(
        default=None,
        description="Maximum concurrent handler invocations. None means runtime default.",
        ge=1,
    )
    execution_timeout_ms: int | None = Field(
        default=None,
        description="Handler execution timeout in milliseconds. None means no timeout.",
        ge=1,
    )
    retry_attempts: int = Field(
        default=0,
        description="Number of retry attempts on transient failure.",
        ge=0,
    )
    idempotent: bool = Field(
        default=False,
        description="Whether handler invocations are safe to retry with the same input.",
    )
