# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Domain queries model for YAML schema validation."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class ModelDomainQueries(BaseModel):
    """Domain query configuration.

    Specifies domain-specific query patterns and implementations.
    """

    model_config = ConfigDict(frozen=True, extra="ignore", from_attributes=True)

    domain: str | None = None
    implementation: str | None = None


__all__ = ["ModelDomainQueries"]
