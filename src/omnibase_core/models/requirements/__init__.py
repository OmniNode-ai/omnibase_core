"""
Requirements models for expressing requirements with graduated strictness.

This module provides models for expressing requirements across four tiers:
- must: Hard requirements that MUST be satisfied
- prefer: Soft preferences that improve score if satisfied
- forbid: Exclusions that MUST NOT be present
- hints: Non-binding hints for tie-breaking
"""

from omnibase_core.models.requirements.model_requirement_set import (
    ModelRequirementSet,
)

__all__ = [
    "ModelRequirementSet",
]
