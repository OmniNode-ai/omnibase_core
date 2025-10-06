#!/usr/bin/env python3
"""
Model Configuration for ONEX Error Details - ONEX Standards Compliant.

Strongly-typed configuration class for ONEX error details.
"""

from datetime import datetime
from uuid import UUID


class ModelConfig:
    """Pydantic configuration for ONEX error details."""

    json_encoders = {
        datetime: lambda v: v.isoformat(),
        UUID: lambda v: str(v),
    }
    frozen = True
