"""
Effect Observability Model - ONEX Standards Compliant.

VERSION: 1.0.0 - INTERFACE LOCKED FOR CODE GENERATION

Observability configuration for effect operations.
Controls logging, metrics emission, and trace propagation.

Implements: OMN-524
"""

from pydantic import BaseModel, ConfigDict, Field

__all__ = ["ModelEffectObservability"]


class ModelEffectObservability(BaseModel):
    """Observability configuration."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    log_request: bool = Field(default=True)
    log_response: bool = Field(default=False, description="May contain sensitive data")
    emit_metrics: bool = Field(default=True)
    trace_propagation: bool = Field(default=True)
