#!/usr/bin/env python3
"""
Service Resolution Result Configuration - ONEX Standards Compliant.

Strongly-typed configuration class for service resolution result.
"""

from pydantic import BaseModel


class ModelConfig(BaseModel):
    """Pydantic model configuration for ONEX compliance."""

    frozen = True
