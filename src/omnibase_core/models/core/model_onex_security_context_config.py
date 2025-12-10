#!/usr/bin/env python3
"""
Model Configuration for ONEX Security Context.

Strongly-typed configuration class for ONEX security context with frozen setting
and custom JSON encoders for UUID and datetime serialization.
"""


class ModelConfig:
    """Pydantic configuration for ONEX security context."""

    frozen = True
    use_enum_values = True
