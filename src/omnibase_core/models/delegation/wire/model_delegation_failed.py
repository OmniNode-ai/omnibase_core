# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Delegation failed terminal wire DTO."""

from __future__ import annotations

from omnibase_core.models.delegation.wire.model_delegation_result import (
    ModelDelegationResult,
)


class ModelDelegationFailed(ModelDelegationResult):
    """Delegation terminal, FAILED outcome (OMN-14600).

    Thin subclass: adds no new fields and no new validation. Class identity
    alone is what class-name to topic routing uses to disambiguate the failed
    terminal outcome.
    """


__all__: list[str] = ["ModelDelegationFailed"]
