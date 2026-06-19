# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Contract entry model for the routing-authority check node."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class ModelRoutingContractEntry(BaseModel):
    """One contract whose model_routing must resolve from authority."""

    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
        from_attributes=True,
    )

    contract_rel: str
    """Path relative to repo_root."""

    required_routing_keys: tuple[str, ...] = (
        "provider",
        "served_model_id",
        "endpoint_ref",
        "routing_source",
    )
