"""
ModelFSMGuard - Guard condition for transition validation.

Generated from FSM subcontract following ONEX contract-driven patterns.
Provides guard condition specification for controlling transition execution.
"""

from enum import Enum
from typing import Dict, Optional, Union

from pydantic import BaseModel, Field


class FSMGuardType(str, Enum):
    """Type of guard conditions for FSM transitions."""

    DATA_VALIDATION = "data_validation"
    STATE_CHECK = "state_check"
    PERMISSION = "permission"
    RESOURCE = "resource"
    CUSTOM = "custom"


class ModelFSMGuard(BaseModel):
    """
    Guard condition that must be satisfied for transition execution.

    Defines conditions that control whether a transition can execute including:
    - Guard identification and classification
    - Boolean condition expression to evaluate
    - Timeout and criticality configuration
    - Parameters for guard evaluation
    """

    # Core identification
    guard_name: str = Field(
        ...,
        description="Unique identifier for the guard",
        pattern=r"^guard_[a-z][a-z0-9_]*$",
        min_length=7,
        max_length=50,
    )

    guard_type: FSMGuardType = Field(..., description="Type of guard condition")

    condition: str = Field(
        ...,
        description="Boolean condition expression to evaluate",
        min_length=1,
        max_length=500,
    )

    description: str = Field(
        ...,
        description="Human-readable description of the guard purpose",
        min_length=5,
        max_length=200,
    )

    # Guard configuration
    timeout_ms: int = Field(
        default=100,
        description="Timeout for guard evaluation in milliseconds",
        ge=10,
        le=5000,
    )

    is_critical: bool = Field(
        default=True,
        description="Whether failure of this guard should abort transition",
    )

    parameters: Dict[str, Union[str, int, float, bool]] = Field(
        default_factory=dict,
        description="Parameters for guard evaluation with strongly typed values",
    )

    class Config:
        json_schema_extra = {
            "example": {
                "guard_name": "guard_adapter_configs_valid",
                "guard_type": "data_validation",
                "condition": "adapter_configs is not None and len(adapter_configs) > 0",
                "description": "Validate that adapter configurations are provided",
                "timeout_ms": 100,
                "is_critical": True,
                "parameters": {
                    "min_adapters": 1,
                    "required_fields": ["name", "version"],
                },
            }
        }
