"""
Effect Response Handling Model - ONEX Standards Compliant.

VERSION: 1.0.0 - INTERFACE LOCKED FOR CODE GENERATION

Response extraction and validation configuration for effect operations.
Defines success codes, field extraction, and extraction engine settings.

Implements: OMN-524
"""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

__all__ = ["ModelEffectResponseHandling"]


class ModelEffectResponseHandling(BaseModel):
    """Response extraction and validation."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    success_codes: list[int] = Field(default_factory=lambda: [200, 201, 202, 204])
    extract_fields: dict[str, str] = Field(
        default_factory=dict, description="Map of output_name -> JSONPath expression"
    )
    fail_on_empty: bool = Field(
        default=False, description="Fail if extraction returns empty"
    )

    # Explicit extraction engine - prevents silent fallback behavior
    extraction_engine: Literal["jsonpath", "dotpath"] = Field(
        default="jsonpath",
        description="Extraction engine. 'jsonpath' requires jsonpath-ng (fails at load if missing), "
        "'dotpath' uses simple $.field.subfield semantics.",
    )
