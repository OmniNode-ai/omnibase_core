"""
Detection result models for sensitive information detection.

Re-exports detection-related enums and models for convenient access.
"""

from omnibase_core.enums.enum_detection_method import EnumDetectionMethod
from omnibase_core.enums.enum_detection_type import EnumDetectionType
from omnibase_core.enums.enum_sensitivity_level import EnumSensitivityLevel

from .model_detection_match import ModelDetectionMatch
from .model_detectionresult import ModelDetectionResult

__all__ = [
    "EnumDetectionMethod",
    "EnumDetectionType",
    "EnumSensitivityLevel",
    "ModelDetectionMatch",
    "ModelDetectionResult",
]
