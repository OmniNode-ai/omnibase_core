#!/usr/bin/env python3
"""
Model Configuration for Container Instance - ONEX Standards Compliant.

Strongly-typed configuration class for container instance.
"""

from datetime import datetime


class ModelConfig:
    """Pydantic configuration for container instance."""

    json_encoders = {
        datetime: lambda v: v.isoformat(),
    }
    frozen = False
