# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""The runtime bus binding: how the runtime bus is bound and, for in-memory, which forwarder carries it."""

from __future__ import annotations

from collections.abc import Callable, Sequence
from importlib.metadata import entry_points
from typing import Final, Self, cast

from pydantic import BaseModel, ConfigDict, model_validator

from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.enums.enum_runtime_bus_binding_kind import EnumRuntimeBusBindingKind
from omnibase_core.errors.model_onex_error import ModelOnexError
from omnibase_core.models.event_bus.model_runtime_bus_event import ModelRuntimeBusEvent

RUNTIME_BUS_FORWARDER_ENTRY_POINT_GROUP: Final[str] = "onex.runtime_bus_forwarders"


class ModelRuntimeBusBinding(BaseModel):
    """The runtime bus binding: the kind and, for INMEMORY_FORWARDED, the forwarder entry-point name.

    ``forwarder`` is set only for INMEMORY_FORWARDED; any other kind carries no forwarder.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    kind: EnumRuntimeBusBindingKind
    forwarder: str | None = None
    reason: str | None = None

    @model_validator(mode="after")
    def _forwarder_matches_kind(self) -> Self:
        if self.kind is EnumRuntimeBusBindingKind.INMEMORY_FORWARDED:
            if self.forwarder is None:
                raise ValueError(
                    "INMEMORY_FORWARDED requires a forwarder entry-point name"
                )
        elif self.forwarder is not None:
            raise ValueError("a forwarder is only valid for INMEMORY_FORWARDED")
        return self

    @classmethod
    def unknown(cls, reason: str) -> Self:
        """A binding with no declaration at all."""
        return cls(kind=EnumRuntimeBusBindingKind.UNKNOWN, reason=reason)

    @classmethod
    def hosted(cls) -> Self:
        """The runtime publishes on the host's broker."""
        return cls(kind=EnumRuntimeBusBindingKind.HOSTED)

    @classmethod
    def test(cls) -> Self:
        """In-memory with no forwarder, declared by a test."""
        return cls(kind=EnumRuntimeBusBindingKind.INMEMORY_TEST)

    @classmethod
    def declared_inmemory(cls) -> Self:
        """The caller declares an in-memory runtime; resolve the forwarder from the entry-point group.

        No provider -> INMEMORY_UNFORWARDED. Exactly one -> INMEMORY_FORWARDED.
        More than one -> INMEMORY_UNFORWARDED naming the providers (never let install order pick).
        """
        providers = list(entry_points(group=RUNTIME_BUS_FORWARDER_ENTRY_POINT_GROUP))
        if not providers:
            return cls(
                kind=EnumRuntimeBusBindingKind.INMEMORY_UNFORWARDED,
                reason="no runtime bus forwarder is installed under onex.runtime_bus_forwarders",
            )
        if len(providers) > 1:
            found = ", ".join(sorted(f"{ep.name} ({ep.value})" for ep in providers))
            return cls(
                kind=EnumRuntimeBusBindingKind.INMEMORY_UNFORWARDED,
                reason=f"more than one runtime bus forwarder is registered ({found}); uninstall the extra provider so one declaration answers",
            )
        return cls(
            kind=EnumRuntimeBusBindingKind.INMEMORY_FORWARDED,
            forwarder=providers[0].name,
        )

    def load_forward(self) -> Callable[[Sequence[ModelRuntimeBusEvent]], object]:
        """Load the forwarder for an INMEMORY_FORWARDED binding and return its ``forward`` callable.

        Raises ModelOnexError when the entry point is missing, fails to load, or has no callable ``forward``.
        """
        if self.kind is not EnumRuntimeBusBindingKind.INMEMORY_FORWARDED:
            raise ModelOnexError(
                "load_forward is only valid for INMEMORY_FORWARDED",
                error_code=EnumCoreErrorCode.CONFIGURATION_ERROR,
            )
        if self.forwarder is None:
            raise ModelOnexError(
                "INMEMORY_FORWARDED binding has no forwarder entry-point name",
                error_code=EnumCoreErrorCode.CONFIGURATION_ERROR,
            )
        providers = list(entry_points(group=RUNTIME_BUS_FORWARDER_ENTRY_POINT_GROUP))
        ep = next((p for p in providers if p.name == self.forwarder), None)
        if ep is None:
            raise ModelOnexError(
                f"runtime bus forwarder entry point {self.forwarder!r} is not registered under {RUNTIME_BUS_FORWARDER_ENTRY_POINT_GROUP}",
                error_code=EnumCoreErrorCode.CONFIGURATION_ERROR,
            )
        try:
            loaded = ep.load()
        except (ImportError, AttributeError, ModuleNotFoundError) as exc:
            raise ModelOnexError(
                f"runtime bus forwarder entry point {self.forwarder!r} failed to load: {exc}",
                error_code=EnumCoreErrorCode.CONFIGURATION_ERROR,
            ) from exc
        forwarder = loaded() if isinstance(loaded, type) else loaded
        forward = getattr(forwarder, "forward", None)
        if not callable(forward):
            raise ModelOnexError(
                f"runtime bus forwarder {self.forwarder!r} does not provide a callable forward",
                error_code=EnumCoreErrorCode.CONFIGURATION_ERROR,
            )
        return cast("Callable[[Sequence[ModelRuntimeBusEvent]], object]", forward)


__all__ = ["RUNTIME_BUS_FORWARDER_ENTRY_POINT_GROUP", "ModelRuntimeBusBinding"]
