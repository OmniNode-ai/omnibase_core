#!/usr/bin/env python3
"""
Model Configuration for ONEX Reply - ONEX Standards Compliant.

Strongly-typed configuration class for ONEX reply with frozen setting
and custom JSON encoders for UUID and datetime serialization.
"""

from datetime import datetime
from uuid import UUID


class ModelConfig:
    """Pydantic configuration for ONEX reply."""

    frozen = True
    use_enum_values = True
