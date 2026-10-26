# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Lease kind registration declared by the contract that uses it."""

from pydantic import BaseModel, ConfigDict, Field


class ModelContractLease(BaseModel):
    """Required lease identity and TTL bound, with optional capacity and renewal policy."""

    model_config = ConfigDict(
        frozen=True, extra="forbid", from_attributes=True, str_strip_whitespace=True
    )

    kind: str = Field(
        min_length=1, description="Lease kind registered at contract load."
    )
    max_ttl_s: int = Field(gt=0, description="Maximum grant TTL in seconds.")
    capacity: int | None = Field(default=None, gt=0)
    renewable: bool | None = Field(default=None)
