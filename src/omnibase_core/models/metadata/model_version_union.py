from __future__ import annotations

from typing import Dict, TypedDict, Union

from pydantic import Field, model_validator

from omnibase_core.errors.model_onex_error import ModelOnexError
from omnibase_core.models.core.model_semver import ModelSemVer

"""
Version Union Model.

Discriminated union for version types following ONEX one-model-per-file architecture.
"""


from typing import TypedDict

from pydantic import BaseModel, Field, model_validator

from omnibase_core.enums.enum_version_union_type import EnumVersionUnionType
from omnibase_core.errors.error_codes import EnumCoreErrorCode
from omnibase_core.errors.model_onex_error import ModelOnexError

from .model_semver import ModelSemVer
from .model_versionunion import ModelVersionUnion


class TypedDictVersionDict(TypedDict):
    """Structured version dict[str, Any]ionary type."""

    major: int
    minor: int
    patch: int


__all__ = ["ModelVersionUnion", "ModelTypedDictVersionDict"]
