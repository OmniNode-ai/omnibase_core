# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Untrusted contract document used for structural binding inspection."""

from typing import Self

import yaml
from pydantic import BaseModel, ConfigDict

from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.errors.model_onex_error import ModelOnexError


class ModelFlipBindingDocument(BaseModel):
    """Retain contract fields without imposing a particular repository's schema.

    Binding inspection supports historical and foreign node contracts. A scalar
    document remains distinguishable from an empty mapping, and fields unrelated
    to binding resolution are retained instead of being silently discarded.
    """

    model_config = ConfigDict(extra="forbid", frozen=True, from_attributes=True)

    mapping: dict[str, object] | None

    @classmethod
    def from_yaml(cls, source: str) -> Self:
        """Parse and validate a document, preserving YAML's non-mapping outcome."""
        try:
            document = yaml.safe_load(source)
        except yaml.YAMLError as exc:
            raise ModelOnexError(
                message=f"Binding contract YAML is invalid: {exc}",
                error_code=EnumCoreErrorCode.CONFIGURATION_PARSE_ERROR,
            ) from exc
        mapping = (
            {key: value for key, value in document.items() if isinstance(key, str)}
            if isinstance(document, dict)
            else None
        )
        return cls.model_validate({"mapping": mapping})
