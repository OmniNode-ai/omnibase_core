# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Typed YAML fields consumed by the demo-path topic coherence validator."""

from __future__ import annotations

from typing import Self

import yaml
from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.errors.model_onex_error import ModelOnexError


class ModelDemoPathYamlContract(BaseModel):
    """Validate the demo-path metadata and event-bus declarations in a contract."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    is_demo_path: bool = Field(default=False)
    widget_topics: list[str] = Field(default_factory=list)
    subscribe_topics: list[str] = Field(default_factory=list)
    publish_topics: list[str] = Field(default_factory=list)

    @classmethod
    def from_yaml(cls, content: str) -> Self:
        """Parse a full contract and validate its selected demo-path fields."""
        try:
            document = yaml.safe_load(content)
        except yaml.YAMLError as exc:
            raise ModelOnexError(
                message=f"Demo-path contract YAML is invalid: {exc}",
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
            ) from exc
        if not isinstance(document, dict):
            raise ModelOnexError(
                message="Demo-path contract root must be a mapping",
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
            )

        metadata = document.get("metadata")
        event_bus = document.get("event_bus")
        metadata = metadata if isinstance(metadata, dict) else {}
        event_bus = event_bus if isinstance(event_bus, dict) else {}
        return cls.model_validate(
            {
                "is_demo_path": metadata.get("demo_path", False),
                "widget_topics": metadata.get("widget_topics", []),
                "subscribe_topics": event_bus.get("subscribe_topics", []),
                "publish_topics": event_bus.get("publish_topics", []),
            }
        )


__all__ = ["ModelDemoPathYamlContract"]
