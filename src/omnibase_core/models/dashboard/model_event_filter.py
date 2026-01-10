# SPDX-FileCopyrightText: 2025 OmniNode Team <info@omninode.ai>
#
# SPDX-License-Identifier: Apache-2.0
"""Event filter configuration model."""

from pydantic import BaseModel, ConfigDict, Field

__all__ = ["ModelEventFilter"]


class ModelEventFilter(BaseModel):
    """Filter configuration for event feed."""

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    event_types: tuple[str, ...] = Field(
        default=(), description="Event types to include (empty = all)"
    )
    severity_levels: tuple[str, ...] = Field(
        default=(), description="Severity levels to include (empty = all)"
    )
    sources: tuple[str, ...] = Field(
        default=(), description="Event sources to include (empty = all)"
    )
