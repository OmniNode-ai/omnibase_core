# Avoid circular import - ModelOnexError should be imported from errors module directly
# from omnibase_core.errors.model_onex_error import ModelOnexError
from omnibase_core.models.common.model_error_context import ModelErrorContext
from omnibase_core.models.common.model_schema_value import ModelSchemaValue

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
    events,
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
    "events",
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
