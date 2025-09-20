"""
OmniBase Core Models

Organized by domain for better maintainability and discoverability.
"""

# Import all domain modules for easy access
from . import (
    cli,
    config,
    connections,
    data,
    infrastructure,
    metadata,
    nodes,
    validation,
)

# Re-export key models for convenience
from .infrastructure import Result, err, ok
from .validation import ModelValidationError

__all__ = [
    # Domain modules
    "cli",
    "config",
    "connections",
    "data",
    "infrastructure",
    "metadata",
    "nodes",
    "validation",
    # Commonly used models
    "Result",
    "ok",
    "err",
    "ModelValidationError",
]
