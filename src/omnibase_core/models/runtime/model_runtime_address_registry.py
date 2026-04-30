# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""Registry model for addressable ONEX runtimes."""

from __future__ import annotations

from collections.abc import Hashable, Iterable
from typing import Self

from pydantic import BaseModel, ConfigDict, Field, model_validator

from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.models.errors.model_onex_error import ModelOnexError
from omnibase_core.models.runtime.model_runtime_address import ModelRuntimeAddress


class ModelRuntimeAddressRegistry(BaseModel):
    """Validated set of runtimes that may be targeted by address or capability."""

    model_config = ConfigDict(
        strict=True,
        frozen=True,
        extra="forbid",
        from_attributes=True,
    )

    runtimes: tuple[ModelRuntimeAddress, ...] = Field(
        default_factory=tuple,
        description="Known addressable runtime instances.",
    )

    @model_validator(mode="after")
    def _validate_unique_runtime_resources(self) -> Self:
        self._assert_unique("address", [runtime.address for runtime in self.runtimes])
        self._assert_unique(
            "runtime_id", [runtime.runtime_id for runtime in self.runtimes]
        )

        scoped_ingress = [
            (runtime.box_id, runtime.ingress_transport, runtime.ingress_address)
            for runtime in self.runtimes
        ]
        self._assert_unique("box-scoped ingress", scoped_ingress)

        scoped_groups = [
            (runtime.box_id, runtime.consumer_group_prefix) for runtime in self.runtimes
        ]
        self._assert_unique("box-scoped consumer_group_prefix", scoped_groups)

        scoped_state_roots = [
            (runtime.box_id, runtime.state_root)
            for runtime in self.runtimes
            if runtime.state_root is not None
        ]
        self._assert_unique("box-scoped state_root", scoped_state_roots)

        scoped_compose_projects = [
            (runtime.box_id, runtime.compose_project)
            for runtime in self.runtimes
            if runtime.compose_project is not None
        ]
        self._assert_unique("box-scoped compose_project", scoped_compose_projects)
        return self

    @staticmethod
    def _assert_unique(label: str, values: Iterable[Hashable]) -> None:
        seen: set[Hashable] = set()
        for value in values:
            if value in seen:
                # error-ok: Pydantic model_validator requires ValueError for aggregation
                raise ValueError(f"duplicate runtime {label}: {value}")
            seen.add(value)

    def get(self, address: str) -> ModelRuntimeAddress:
        """Return a runtime by exact address."""
        for runtime in self.runtimes:
            if runtime.address == address:
                return runtime
        raise ModelOnexError(
            message=f"unknown runtime address: {address}",
            error_code=EnumCoreErrorCode.RESOURCE_NOT_FOUND,
            address=address,
        )

    def by_capabilities(
        self,
        required_capabilities: tuple[str, ...],
        *,
        box_id: str | None = None,
    ) -> tuple[ModelRuntimeAddress, ...]:
        """Return runtimes that satisfy the required capabilities."""
        return tuple(
            runtime
            for runtime in self.runtimes
            if runtime.has_capabilities(required_capabilities)
            and (box_id is None or runtime.box_id == box_id)
        )


__all__ = ["ModelRuntimeAddressRegistry"]
