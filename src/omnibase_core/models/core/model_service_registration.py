#!/usr/bin/env python3
"""
Service Registration Model - ONEX Standards Compliant.

Strongly-typed model for service registration entries in container.
"""

from typing import Any

from pydantic import BaseModel, Field


class ModelServiceRegistration(BaseModel):
    """Service registration entry in container."""

    service_name: str = Field(description="Unique service identifier")
    implementation_class: str = Field(description="Full class path for implementation")
    initialization_params: dict[str, str] = Field(
        default_factory=dict,
        description="Initialization parameters",
    )
    is_singleton: bool = Field(default=True, description="Whether service is singleton")
