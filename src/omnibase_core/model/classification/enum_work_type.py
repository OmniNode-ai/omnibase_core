"""
Enum for work types.

Defines the types of work that can be classified.
"""

from enum import Enum


class EnumWorkType(str, Enum):
    """Types of work that can be classified."""

    MODEL_GENERATION = "model_generation"
    CODE_FORMATTING = "code_formatting"
    DOCUMENTATION = "documentation"
    TESTING = "testing"
    REFACTORING = "refactoring"
    BUG_FIX = "bug_fix"
    FEATURE = "feature"
    ARCHITECTURE = "architecture"
    DEPLOYMENT = "deployment"
    ANALYSIS = "analysis"
    REVIEW = "review"
    CLEANUP = "cleanup"
