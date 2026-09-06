# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""Immutable environment data supplied by typed bootstrap."""

from __future__ import annotations

from collections.abc import Mapping
from types import MappingProxyType

from pydantic import BaseModel, ConfigDict, Field, model_validator

from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.models.bootstrap.model_injected_environment_value import (
    ModelInjectedEnvironmentValue,
)
from omnibase_core.models.errors.model_onex_error import ModelOnexError


class ModelInjectedEnvironment(BaseModel):
    """Immutable environment data supplied by the explicit bootstrap boundary."""

    entries: tuple[ModelInjectedEnvironmentValue, ...] = Field(default_factory=tuple)
    declared_keys: frozenset[str]

    model_config = ConfigDict(extra="forbid", frozen=True)

    @model_validator(mode="after")
    def validate_entries(self) -> ModelInjectedEnvironment:
        """Keep one value per declared key and reject undeclared values."""
        names = [entry.name for entry in self.entries]
        if len(names) != len(set(names)):
            raise ModelOnexError(
                message="Bootstrap environment contains duplicate key entries",
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
            )
        undeclared = set(names) - self.declared_keys
        if undeclared:
            raise ModelOnexError(
                message=(
                    "Bootstrap environment includes undeclared keys: "
                    f"{', '.join(sorted(undeclared))}"
                ),
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
            )
        return self

    @property
    def values(self) -> Mapping[str, str]:
        """Return a read-only view of captured entries."""
        return MappingProxyType({entry.name: entry.value for entry in self.entries})

    def require(self, name: str) -> str:
        """Return a declared value or fail closed."""
        self._validate_declared(name)
        try:
            return self.values[name]
        except KeyError as error:
            raise ModelOnexError(
                message=f"Required bootstrap environment value is missing: {name}",
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
            ) from error

    def optional(self, name: str) -> str | None:
        """Return a declared optional value."""
        self._validate_declared(name)
        return self.values.get(name)

    def _validate_declared(self, name: str) -> None:
        if name not in self.declared_keys:
            raise ModelOnexError(
                message=f"Environment key is not declared by bootstrap: {name}",
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
            )
