#!/usr/bin/env python3
"""
Group Manifest Configuration.

Strongly-typed configuration class for group manifest data.
"""


class ModelConfig:
    """Pydantic model configuration for ONEX compliance."""

    frozen = True
    use_enum_values = True
