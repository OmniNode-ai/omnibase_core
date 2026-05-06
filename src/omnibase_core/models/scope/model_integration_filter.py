# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""ModelIntegrationFilter — scope predicate filter targeting availability of named integrations."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class ModelIntegrationFilter(BaseModel):
    """Predicate filter targeting availability of named integrations."""

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    linear: dict[str, str] | None = Field(
        default=None,
        description=(
            "Linear integration requirements. Keys: 'workspace', 'ticket_prefix'."
        ),
    )
    kafka: dict[str, str] | None = Field(
        default=None,
        description="Kafka/Redpanda integration requirements.",
    )


__all__ = ["ModelIntegrationFilter"]
