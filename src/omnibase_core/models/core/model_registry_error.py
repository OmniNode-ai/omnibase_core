"""
Registry Error Model.

Canonical error model for registry errors (tool/handler registries).
"""

from pydantic import Field

from omnibase_core.enums.enum_cli_exit_code import EnumCLIExitCode
from omnibase_core.enums.enum_registry_error_code import EnumRegistryErrorCode
from omnibase_core.models.common.model_onex_warning import ModelOnexWarning


class ModelRegistryError(ModelOnexWarning):
    """
    Canonical error model for registry errors (tool/handler registries).
    Use this for all structured registry error reporting.
    """

    error_code: EnumRegistryErrorCode = Field(
        default=...,
        description="Canonical registry error code.",
    )
