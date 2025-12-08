"""
Effect node models for the ONEX 4-node architecture.

This module contains input/output models for NodeEffect operations,
which handle external I/O (APIs, databases, file systems, message queues).
"""

from omnibase_core.models.effect.model_effect_input import ModelEffectInput
from omnibase_core.models.effect.model_effect_output import ModelEffectOutput

__all__ = [
    "ModelEffectInput",
    "ModelEffectOutput",
]
