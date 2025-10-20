"""
Workflow parameter type enumeration.

Defines types for discriminated union in workflow parameters.
"""

from enum import Enum


class EnumWorkflowParameterType(str, Enum):
    """Workflow parameter type enumeration for discriminated unions."""

    WORKFLOW_CONFIG = "workflow_config"
    EXECUTION_SETTING = "execution_setting"
    TIMEOUT_SETTING = "timeout_setting"
    RESOURCE_LIMIT = "resource_limit"
    ENVIRONMENT_VARIABLE = "environment_variable"


# Export for use
__all__ = ["EnumWorkflowParameterType"]
