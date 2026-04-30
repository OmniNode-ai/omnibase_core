# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""Runtime target selector for explicit and load-balanced routing."""

from __future__ import annotations

from typing import Self

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.enums.enum_runtime_selection_mode import EnumRuntimeSelectionMode
from omnibase_core.models.errors.model_onex_error import ModelOnexError
from omnibase_core.models.runtime.model_runtime_address import ModelRuntimeAddress
from omnibase_core.models.runtime.model_runtime_address_registry import (
    ModelRuntimeAddressRegistry,
)


class ModelRuntimeTargetSelector(BaseModel):
    """Selection request for choosing a target runtime."""

    model_config = ConfigDict(
        strict=True,
        frozen=True,
        extra="forbid",
        from_attributes=True,
    )

    mode: EnumRuntimeSelectionMode = Field(
        ...,
        description="How a runtime should be selected.",
    )
    address: str | None = Field(
        default=None,
        min_length=1,
        description="Exact runtime address for explicit mode.",
    )
    required_capabilities: tuple[str, ...] = Field(
        default_factory=tuple,
        description="Capabilities required from selected runtimes.",
    )
    # string-id-ok: human-readable host or box name
    preferred_box_id: str | None = Field(
        default=None,
        min_length=1,
        description="Optional box preference for capability or load-balanced modes.",
    )
    allow_cross_box: bool = Field(
        default=True,
        description="Whether selection may fall back to runtimes on other boxes.",
    )

    @field_validator("mode", mode="before")
    @classmethod
    def _coerce_mode(cls, value: object) -> object:
        if isinstance(value, str):
            return EnumRuntimeSelectionMode(value)
        return value

    @field_validator("required_capabilities", mode="before")
    @classmethod
    def _coerce_capabilities(cls, value: object) -> object:
        if isinstance(value, list):
            return tuple(value)
        return value

    @field_validator("required_capabilities")
    @classmethod
    def _validate_capabilities(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        normalized: list[str] = []
        seen: set[str] = set()
        for item in value:
            capability = item.strip()
            if not capability:
                raise ValueError("required capability names must be non-empty")
            if capability in seen:
                raise ValueError(f"duplicate required capability: {capability}")
            seen.add(capability)
            normalized.append(capability)
        return tuple(normalized)

    @model_validator(mode="after")
    def _validate_mode_shape(self) -> Self:
        if self.mode is EnumRuntimeSelectionMode.EXPLICIT:
            if self.address is None:
                raise ValueError("explicit runtime selection requires address")
            if self.required_capabilities:
                raise ValueError(
                    "explicit runtime selection must not include required_capabilities"
                )
        elif self.address is not None:
            raise ValueError("address is only valid for explicit runtime selection")
        return self

    def candidates(
        self, registry: ModelRuntimeAddressRegistry
    ) -> tuple[ModelRuntimeAddress, ...]:
        """Return candidate runtimes for this selector."""
        if self.mode is EnumRuntimeSelectionMode.EXPLICIT:
            if self.address is None:
                raise ModelOnexError(
                    message="explicit runtime selection requires address",
                    error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                )
            return (registry.get(self.address),)

        preferred = registry.by_capabilities(
            self.required_capabilities,
            box_id=self.preferred_box_id,
        )
        if preferred or not self.allow_cross_box:
            return preferred
        return registry.by_capabilities(self.required_capabilities)

    def select_first(
        self, registry: ModelRuntimeAddressRegistry
    ) -> ModelRuntimeAddress:
        """Select the first deterministic candidate.

        Runtime load-aware routing should sort candidates before calling this
        method. This method intentionally keeps the core contract pure.
        """
        candidates = self.candidates(registry)
        if not candidates:
            raise ModelOnexError(
                message="no runtime candidates matched selector",
                error_code=EnumCoreErrorCode.RESOURCE_NOT_FOUND,
                selection_mode=self.mode.value,
                required_capabilities=self.required_capabilities,
                preferred_box_id=self.preferred_box_id,
            )
        return candidates[0]


__all__ = ["ModelRuntimeTargetSelector"]
