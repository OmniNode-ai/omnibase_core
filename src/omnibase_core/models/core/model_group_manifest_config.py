#!/usr/bin/env python3
"""
Group Manifest Configuration - ONEX Standards Compliant.

Strongly-typed configuration class for group manifest data.
"""

from omnibase_core.models.core.model_group_manifest import ModelGroupManifest


class ModelConfig:
    """Pydantic model configuration for ONEX compliance."""

    frozen = True
    use_enum_values = True
