# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Permissive view of the integration-skip guard YAML (operational keys only)."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, model_validator

__all__ = ["ModelIntegrationSkipsRawConfig"]


class ModelIntegrationSkipsRawConfig(BaseModel):
    """The guard file as written: unknown informational keys are dropped before validation.

    Values stay ``object`` because the replaced script coerced them itself
    (``bool(...)``, ``int(...)``) and treated falsy values as absent.
    """

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    silent_skip_allowed: object = False
    require_executed_min: object = 1
    required_services: object = None
    allowed_optional_skip_patterns: object = None

    @model_validator(mode="before")
    @classmethod
    def _keep_known_keys(cls, data: object) -> object:
        """Drop the keys this view does not read; the file carries many more."""
        if not isinstance(data, dict):
            return data
        known = (
            "silent_skip_allowed",
            "require_executed_min",
            "required_services",
            "allowed_optional_skip_patterns",
        )
        return {key: value for key, value in data.items() if key in known}
