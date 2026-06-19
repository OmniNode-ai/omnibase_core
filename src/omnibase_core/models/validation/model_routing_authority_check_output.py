# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Output model for the routing-authority check node."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class ModelRoutingAuthorityCheckOutput(BaseModel):
    """Output of the routing-authority check."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    passed: bool
    positive_ok: bool
    negative_ok: bool
    residue_ok: bool
    shape_ok: bool

    positive_proof: dict[str, object]
    negative_audit: dict[str, object]
    residue_audit: dict[str, object]
    provider_endpoint_shape_audit: dict[str, object]

    gate: str = "routing-authority-check"
    ticket: str = "OMN-13306"
    origin_tickets: tuple[str, ...] = ("OMN-12821", "OMN-12877", "OMN-12883")
