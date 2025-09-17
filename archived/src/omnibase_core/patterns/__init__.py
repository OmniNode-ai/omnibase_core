"""
ONEX Patterns Module

This module contains architectural patterns and frameworks that utilize ONEX nodes
to create higher-level orchestration and workflow management capabilities.

Patterns are distinct from nodes themselves - they compose and coordinate existing
node types to create reusable workflow and orchestration solutions.
"""

from .reducer_pattern_engine import *

__all__ = [
    # Re-export all pattern modules
    "reducer_pattern_engine",
]
