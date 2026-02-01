"""Hook registry with freeze-after-init thread safety."""

from omnibase_core.decorators.decorator_error_handling import standard_error_handling
from omnibase_core.models.pipeline import ModelPipelineHook, PipelinePhase
from omnibase_core.pipeline.exceptions import (
    DuplicateHookError,
    HookRegistryFrozenError,
)


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

    Thread Safety
    -------------
    **This class uses a freeze-after-init pattern for thread safety.**

    **Phase 1 - Registration (NOT thread-safe):**

    Before ``freeze()`` is called, the registry is mutable. All registration
    must happen in a single thread during initialization::

        # Single-threaded registration phase
        registry = RegistryHook()
        registry.register(hook1)  # Modifies internal state
        registry.register(hook2)  # Modifies internal state
        registry.freeze()         # Transitions to read-only

    **Phase 2 - After Freeze (Thread-safe for reads):**

    Once ``freeze()`` is called, no further mutations are possible.
    All read operations (``get_hooks_by_phase()``, ``get_all_hooks()``,
    ``get_hook_by_name()``) are safe for concurrent access::

        registry.freeze()

        # Now safe for concurrent reads
        await asyncio.gather(
            worker_1(registry),  # Reads hooks
            worker_2(registry),  # Reads hooks
        )

    **Thread Safety Matrix:**

    ===========================  ============  ======================
    Method                       Thread-Safe?  Notes
    ===========================  ============  ======================
    ``register()``               No            Only before freeze()
    ``freeze()``                 Yes           Idempotent, safe to call multiple times
    ``get_hooks_by_phase()``     Yes*          Returns a copy (safe after freeze)
    ``get_all_hooks()``          Yes*          Returns a copy (safe after freeze)
    ``get_hook_by_name()``       Yes*          Read-only (safe after freeze)
    ``is_frozen``                Yes           Property, read-only
    ===========================  ============  ======================

    *Thread-safe only AFTER ``freeze()`` is called.

    **Note**: The methods return copies of internal lists to prevent
    external modification from affecting the registry state.

    See Also
    --------
    - docs/guides/THREADING.md for comprehensive thread safety guide
    - CLAUDE.md section "Thread Safety" for quick reference
    """

    def __init__(self) -> None:
        """Initialize an empty, unfrozen registry."""
        self._hooks_by_phase: dict[PipelinePhase, list[ModelPipelineHook]] = {}
        self._hooks_by_name: dict[str, ModelPipelineHook] = {}
        self._frozen: bool = False

    @property
    def is_frozen(self) -> bool:
        """Whether the registry is frozen."""
        return self._frozen

    @standard_error_handling("Hook registration")
    def register(self, hook: ModelPipelineHook) -> None:
        """
        Register a hook.

        Args:
            hook: The hook to register.

        Raises:
            HookRegistryFrozenError: If registry is frozen.
            DuplicateHookError: If hook_name already registered.
        """
        if self._frozen:
            raise HookRegistryFrozenError

        if hook.hook_name in self._hooks_by_name:
            raise DuplicateHookError(hook.hook_name)

        self._hooks_by_name[hook.hook_name] = hook

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

    @standard_error_handling("Hooks retrieval by phase")
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

    @standard_error_handling("All hooks retrieval")
    def get_all_hooks(self) -> list[ModelPipelineHook]:
        """
        Get all registered hooks.

        Returns:
            List of all hooks (copy, safe to modify).
        """
        return list(self._hooks_by_name.values())

    @standard_error_handling("Hook retrieval by name")
    def get_hook_by_name(self, hook_name: str) -> ModelPipelineHook | None:
        """
        Get a hook by its name.

        Args:
            hook_name: The hook name to look up.

        Returns:
            The hook if found, None otherwise.
        """
        return self._hooks_by_name.get(hook_name)


__all__ = ["RegistryHook"]
