#!/usr/bin/env python3
"""
Model Configuration for ONEX Reply.

Strongly-typed configuration class for ONEX reply with frozen setting
and custom JSON encoders for UUID and datetime serialization.
"""


class ModelConfig:
    """Pydantic configuration for ONEX reply."""

    frozen = True
    use_enum_values = True
