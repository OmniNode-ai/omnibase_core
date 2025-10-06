from __future__ import annotations

from typing import Dict, TypedDict

from pydantic import Field

from omnibase_core.errors.model_onex_error import ModelOnexError
from omnibase_core.models.core.model_semver import ModelSemVer

"""
Function Deprecation Information Model.

Deprecation and lifecycle information for functions.
Part of the ModelFunctionNodeMetadata restructuring.
"""


from typing import TypedDict

from pydantic import BaseModel, Field

from omnibase_core.enums.enum_deprecation_status import EnumDeprecationStatus
from omnibase_core.errors.error_codes import EnumCoreErrorCode
from omnibase_core.errors.model_onex_error import ModelOnexError
from omnibase_core.models.metadata.model_semver import ModelSemVer

from .model_functiondeprecationinfo import ModelFunctionDeprecationInfo


class ModelDeprecationSummary(TypedDict):
    """Type-safe dict[str, Any]ionary for deprecation summary."""

    is_deprecated: bool
    has_replacement: bool
    deprecated_since: str | None
    replacement: str | None
    status: str  # EnumDeprecationStatus.value


# Export for use
__all__ = ["ModelDeprecationSummary", "ModelFunctionDeprecationInfo"]
