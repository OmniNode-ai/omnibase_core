"""
Enum for token usage categories.

Defines categories of token usage for tracking and analysis.
"""

from enum import Enum


class EnumUsageCategory(str, Enum):
    """Categories of token usage."""

    MODEL_GENERATION = "model_generation"
    CODE_ANALYSIS = "code_analysis"
    TESTING = "testing"
    DOCUMENTATION = "documentation"
    ARCHITECTURE = "architecture"
    DEBUGGING = "debugging"
    REFACTORING = "refactoring"
    REVIEW = "review"
    OTHER = "other"
