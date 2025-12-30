# SPDX-FileCopyrightText: 2025 OmniNode Team <info@omninode.ai>
#
# SPDX-License-Identifier: Apache-2.0
"""Hook registry with freeze-after-init thread safety."""

from omnibase_core.pipeline.exceptions import (
    DuplicateHookError,
    HookRegistryFrozenError,
)
from omnibase_core.pipeline.models import ModelPipelineHook, PipelinePhase


class RegistryHook:
    """
    Registry for pipeline hooks with freeze-after-init thread safety.

    Registration phase: single-threaded, mutable
    After freeze(): immutable, concurrency-safe

    Usage:
        registry = RegistryHook()
        registry.register(hook1)
        registry.register(hook2)
        registry.freeze()  # Lock for concurrent access
        # Now safe for concurrent reads
    """

    def __init__(self) -> None:
        """Initialize an empty, unfrozen registry."""
        self._hooks_by_phase: dict[PipelinePhase, list[ModelPipelineHook]] = {}
        self._hooks_by_id: dict[str, ModelPipelineHook] = {}
        self._frozen: bool = False

    @property
    def is_frozen(self) -> bool:
        """Whether the registry is frozen."""
        return self._frozen

    def register(self, hook: ModelPipelineHook) -> None:
        """
        Register a hook.

        Args:
            hook: The hook to register.

        Raises:
            HookRegistryFrozenError: If registry is frozen.
            DuplicateHookError: If hook_id already registered.
        """
        if self._frozen:
            raise HookRegistryFrozenError

        if hook.hook_id in self._hooks_by_id:
            raise DuplicateHookError(hook.hook_id)

        self._hooks_by_id[hook.hook_id] = hook

        if hook.phase not in self._hooks_by_phase:
            self._hooks_by_phase[hook.phase] = []
        self._hooks_by_phase[hook.phase].append(hook)

    def freeze(self) -> None:
        """
        Freeze the registry, preventing further modifications.

        After freezing, the registry is safe for concurrent reads.
        Calling freeze() multiple times is safe (idempotent).
        """
        self._frozen = True

    def get_hooks_by_phase(self, phase: PipelinePhase) -> list[ModelPipelineHook]:
        """
        Get all hooks registered for a phase.

        Returns a copy to ensure thread safety.

        Args:
            phase: The pipeline phase.

        Returns:
            List of hooks (copy, safe to modify).
        """
        return list(self._hooks_by_phase.get(phase, []))

    def get_all_hooks(self) -> list[ModelPipelineHook]:
        """
        Get all registered hooks.

        Returns:
            List of all hooks (copy, safe to modify).
        """
        return list(self._hooks_by_id.values())

    def get_hook_by_id(self, hook_id: str) -> ModelPipelineHook | None:
        """
        Get a hook by its ID.

        Args:
            hook_id: The hook ID to look up.

        Returns:
            The hook if found, None otherwise.
        """
        return self._hooks_by_id.get(hook_id)


# Backwards compatibility alias
HookRegistry = RegistryHook

__all__ = ["RegistryHook", "HookRegistry"]
