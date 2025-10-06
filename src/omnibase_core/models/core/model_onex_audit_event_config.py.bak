#!/usr/bin/env python3
"""
Model Configuration for ONEX Audit Event - ONEX Standards Compliant.

Strongly-typed configuration class for ONEX audit event.
"""

from datetime import datetime
from uuid import UUID


class ModelConfig:
    """Pydantic configuration for ONEX audit event."""

    json_encoders = {
        datetime: lambda v: v.isoformat(),
        UUID: lambda v: str(v),
    }
    frozen = True
