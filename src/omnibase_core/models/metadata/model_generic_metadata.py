from __future__ import annotations

import uuid
from typing import TYPE_CHECKING, Any, Dict, Generic, TypedDict

from pydantic import Field, field_validator

from omnibase_core.errors.model_onex_error import ModelOnexError
from omnibase_core.models.core.model_semver import ModelSemVer

"""
Generic metadata model for flexible data storage.
"""


# Import proper type with fallback mechanism from metadata package
from typing import TypedDict, overload
from uuid import UUID

# Import simplified type constraint from core
from omnibase_core.types.constraints import BasicValueType

from .model_genericmetadata import ModelGenericMetadata

if TYPE_CHECKING:
    from . import ProtocolSupportedMetadataType
else:
    # Runtime fallback - will be dict[str, object] from __init__.py
    ProtocolSupportedMetadataType = dict[str, object]  # type: ignore[misc]

from pydantic import BaseModel, Field, field_validator

from omnibase_core.errors.error_codes import EnumCoreErrorCode
from omnibase_core.errors.model_onex_error import ModelOnexError
from omnibase_core.models.common.model_error_context import ModelErrorContext
from omnibase_core.models.common.model_schema_value import ModelSchemaValue
from omnibase_core.models.infrastructure.model_cli_value import ModelCliValue

from .model_semver import ModelSemVer, parse_semver_from_string

# Use simplified BasicValueType from core constraints instead of redundant TypeVar


# TypedDict for protocol method parameters
class TypedDictGenericMetadataDict(TypedDict, total=False):
    """Typed structure for generic metadata dict[str, Any]ionary in protocol methods."""

    metadata_id: UUID | None
    metadata_display_name: str | None
    description: str | None
    version: ModelSemVer | None
    tags: list[str]
    custom_fields: dict[str, object]
