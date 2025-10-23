"""
Deduplication Models - Abstract bases for idempotent action processing.

Provides abstract base classes for action deduplication in at-least-once
delivery systems.

Author: ONEX Framework Team
Version: 1.0.0
"""

from .model_action_dedup_base import ModelActionDedupBase

__all__ = [
    "ModelActionDedupBase",
]
