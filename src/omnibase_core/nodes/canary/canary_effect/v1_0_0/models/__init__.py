#!/usr/bin/env python3
"""
Canary Effect Models Package - Contract-Driven Implementation.

Strongly typed Pydantic models generated from ONEX contract specifications.
Replaces previous architecture violations with proper contract-driven models.

Contract Reference:
    - Source: canary_effect_contract.yaml
    - Node Type: EFFECT
    - Strong Typing: Zero Any types, full Pydantic validation
    - ONEX Compliance: Contract-driven model generation
"""

from .model_canary_effect_input import (
    EnumCanaryOperationType,
    ModelCanaryEffectInput,
)
from .model_canary_effect_output import ModelCanaryEffectOutput

__all__ = [
    # Input models - contract-driven from input_state schema
    "ModelCanaryEffectInput",
    "EnumCanaryOperationType",
    # Output models - contract-driven from output_state schema
    "ModelCanaryEffectOutput",
]
