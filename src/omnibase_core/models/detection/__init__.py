# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""
Detection domain models for ONEX.
"""

from .model_detection_rule_metadata import ModelDetectionRuleMetadata
from .model_service_detection_config import ModelServiceDetectionConfig

__all__: list[str] = ["ModelDetectionRuleMetadata", "ModelServiceDetectionConfig"]

# Resolve forward references for ModelServiceDetectionConfig.health_check field
# ModelHealthCheck is imported under TYPE_CHECKING to avoid circular imports
try:
    from omnibase_core.models.health.model_health_check import (
        ModelHealthCheck,  # noqa: F401
    )

    ModelServiceDetectionConfig.model_rebuild(raise_errors=False)
except ImportError:
    # The model is rebuilt by the importing module once the health types load.
    pass
