"""
Registry Error Model.

Canonical error model for registry errors (tool/handler registries).
"""

from pydantic import Field

from omnibase_core.models.common.model_onex_warning import ModelOnexWarning
from omnibase_core.models.core.model_core_errors import (
    EnumCLIExitCode,
    ModelRegistryErrorCode,
)


class ModelRegistryErrorModel(ModelOnexWarning):
    """
    Canonical error model for registry errors (tool/handler registries).
    Use this for all structured registry error reporting.
    """

    error_code: ModelRegistryErrorCode = Field(
        ...,
        description="Canonical registry error code.",
    )
