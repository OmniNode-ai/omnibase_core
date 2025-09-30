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
    results,
    validation,
)

# Re-export key models for convenience
from .common import (
    ModelErrorContext,
    ModelNumericValue,
    ModelOnexError,
    ModelSchemaValue,
)
from .infrastructure import err, ok
from .model_yaml_dump_options import ModelYamlDumpOptions
from .results import ModelOnexResult
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
    "results",
    "validation",
    # Commonly used models
    "ModelErrorContext",
    "ModelNumericValue",
    "ModelOnexError",
    "ModelOnexResult",
    "ModelSchemaValue",
    "ModelYamlDumpOptions",
    "ok",
    "err",
    "ModelValidationError",
]
