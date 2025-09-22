"""
OmniBase Core Models

Organized by domain for better maintainability and discoverability.
"""

# Import all domain modules for easy access
from . import (
    cli,
    common,
    config,
    connections,
    contracts,
    core,
    infrastructure,
    metadata,
    nodes,
    validation,
)

# Re-export key models for convenience
from .common import ModelErrorContext, ModelOnexError, ModelSchemaValue
from .infrastructure import Result, err, ok
from .validation import ModelValidationError

__all__ = [
    # Domain modules
    "cli",
    "common",
    "config",
    "connections",
    "contracts",
    "core",
    "infrastructure",
    "metadata",
    "nodes",
    "validation",
    # Commonly used models
    "ModelErrorContext",
    "ModelOnexError",
    "ModelSchemaValue",
    "Result",
    "ok",
    "err",
    "ModelValidationError",
]
