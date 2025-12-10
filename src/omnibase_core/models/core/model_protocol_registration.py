#!/usr/bin/env python3
"""
Protocol Registration Model.

Strongly-typed model for protocol registration entries in container.
"""

from pydantic import BaseModel, Field


class ModelProtocolRegistration(BaseModel):
    """Protocol registration entry in container."""

    protocol_name: str = Field(description="Protocol identifier")
    implementation_class: str = Field(description="Full class path for implementation")
    binding_strategy: str = Field(
        default="duck_typing",
        description="How protocol is bound to implementation",
    )
