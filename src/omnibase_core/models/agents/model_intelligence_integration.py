# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Intelligence integration model for YAML schema validation."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict

from omnibase_core.types.typed_dict_codanna_integration import (
    TypedDictCodannaIntegration,
)


class ModelIntelligenceIntegration(BaseModel):
    """Intelligence system integration.

    Configures integration with AI/ML intelligence services including
    quality assessment, performance optimization, and Codanna.
    """

    model_config = ConfigDict(frozen=True, extra="ignore", from_attributes=True)

    quality_assessment: list[str] | None = None
    performance_optimization: list[str] | None = None
    codanna_integration: TypedDictCodannaIntegration | None = None


__all__ = ["ModelIntelligenceIntegration"]
