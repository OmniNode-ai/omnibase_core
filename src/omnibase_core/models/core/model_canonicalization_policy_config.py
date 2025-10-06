#!/usr/bin/env python3
"""
Model Configuration for Canonicalization Policy - ONEX Standards Compliant.

Strongly-typed configuration class for canonicalization policy.
"""

from datetime import datetime

from omnibase_core.models.core.model_canonicalization_policy import (
    ModelCanonicalizationPolicy,
)


class ModelConfig:
    """Configuration for ModelCanonicalizationPolicy."""

    arbitrary_types_allowed = True
    json_encoders = {
        datetime: lambda v: v.isoformat(),
        ModelCanonicalizationPolicy: lambda v: v.model_dump(),
    }
