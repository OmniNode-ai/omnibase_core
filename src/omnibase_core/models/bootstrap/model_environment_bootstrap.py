# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""The typed boundary that materializes declared process environment."""

from __future__ import annotations

import os
from collections.abc import Collection, Mapping

from pydantic import BaseModel, ConfigDict

from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.models.bootstrap.model_injected_environment import (
    ModelInjectedEnvironment,
)
from omnibase_core.models.bootstrap.model_injected_environment_value import (
    ModelInjectedEnvironmentValue,
)
from omnibase_core.models.errors.model_onex_error import ModelOnexError


class ModelEnvironmentBootstrap(BaseModel):
    """Validated, one-time materialization of declared process-environment keys."""

    environment: ModelInjectedEnvironment

    model_config = ConfigDict(extra="forbid", frozen=True)

    @classmethod
    def capture_process_environment(
        cls,
        *,
        declared_keys: Collection[str],
    ) -> ModelEnvironmentBootstrap:
        """Capture only declared keys from the process at bootstrap."""
        return cls.from_mapping(os.environ, declared_keys=declared_keys)

    @classmethod
    def from_mapping(
        cls,
        values: Mapping[str, str],
        *,
        declared_keys: Collection[str],
    ) -> ModelEnvironmentBootstrap:
        """Build injected configuration from a supplied mapping."""
        declared = frozenset(declared_keys)
        if not declared:
            raise ModelOnexError(
                message="Bootstrap must declare at least one environment key",
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
            )
        return cls(
            environment=ModelInjectedEnvironment(
                declared_keys=declared,
                entries=tuple(
                    ModelInjectedEnvironmentValue(name=key, value=values[key])
                    for key in sorted(declared)
                    if key in values
                ),
            )
        )
