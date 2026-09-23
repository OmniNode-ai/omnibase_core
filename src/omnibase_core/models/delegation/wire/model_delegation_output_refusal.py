# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Typed terminal refusal for an output that lacks a declared deliverable."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict

from omnibase_core.enums.enum_delegation_output_refusal_reason import (
    EnumDelegationOutputRefusalReason,
)
from omnibase_core.enums.enum_delegation_output_shape import EnumDelegationOutputShape


class ModelDelegationOutputRefusal(BaseModel):
    """Why a raw model response cannot be returned under its declared contract."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    reason: EnumDelegationOutputRefusalReason
    output_shape: EnumDelegationOutputShape
    contract_failure_reasons: tuple[str, ...]


__all__ = ["ModelDelegationOutputRefusal"]
