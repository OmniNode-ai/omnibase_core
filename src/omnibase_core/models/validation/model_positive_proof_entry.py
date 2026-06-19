# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Positive proof entry model for the routing-authority check node."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class ModelPositiveProofEntry(BaseModel):
    """Route-source proof for one demo-path contract."""

    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
        from_attributes=True,
    )

    contract: str
    provider: str | None
    model: str | None
    endpoint_ref: str | None
    endpoint: str | None
    route_source: str | None
    field_sources: dict[str, str]
    endpoint_source: str
