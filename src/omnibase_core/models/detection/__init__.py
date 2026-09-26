# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""
Detection domain models for ONEX.
"""

from pydantic.errors import PydanticUndefinedAnnotation

from .model_detection_rule_metadata import ModelDetectionRuleMetadata
from .model_service_detection_config import ModelServiceDetectionConfig

__all__: list[str] = ["ModelDetectionRuleMetadata", "ModelServiceDetectionConfig"]

# Resolve forward references for ModelServiceDetectionConfig.health_check field
# ModelHealthCheck is imported under TYPE_CHECKING to avoid circular imports
try:
    from omnibase_core.models.health.model_health_check import (
        ModelHealthCheck,  # noqa: F401
    )

    ModelServiceDetectionConfig.model_rebuild()
except (ImportError, PydanticUndefinedAnnotation):
    # Forward reference not resolvable at this import point (cycle not yet closed);
    # the importer that closes the cycle rebuilds it. Every other error propagates.
    pass
