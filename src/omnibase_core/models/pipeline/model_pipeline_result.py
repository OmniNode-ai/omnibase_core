"""Pipeline result model for execution outcomes."""

from collections.abc import Mapping, Sequence
from copy import deepcopy
from types import MappingProxyType
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator

from omnibase_core.models.pipeline.model_hook_error import ModelHookError
from omnibase_core.models.pipeline.model_pipeline_context import ModelPipelineContext


class ModelPipelineResult(BaseModel):
    """
    Result of pipeline execution.

    Contains success status, any captured errors (from continue phases),
    and the final context state.

    Thread Safety
    -------------
    **Thread-safe with defensive copying.**

    This model uses ``frozen=True``, making the result itself immutable.
    All mutable input data is defensively copied on construction:

    - **errors**: Automatically converted to immutable tuple if passed as list
    - **context**: Deep copy of context data created on initialization

    This ensures that external code cannot modify the result's state after
    creation, even if it holds references to the original mutable objects.

    Immutable Fields (Thread-Safe)
    ------------------------------
    - ``success``: bool (immutable by nature)
    - ``errors``: tuple of ModelHookError (immutable tuple, frozen models)
    - ``context``: ModelPipelineContext (defensive copy on init - data isolated)

    Defensive Copying
    -----------------
    The ``_create_defensive_context_copy`` validator ensures that:

    1. A new ModelPipelineContext is created with deep-copied data
    2. No external references to the original data dict are retained
    3. Modifications to the original context after result creation have no effect

    Similarly, ``_ensure_errors_immutable`` converts any list of errors to a tuple.

    .. note:: **Context is Still Technically Mutable**

        While the context data is deep-copied on construction (breaking external
        references), the ``ModelPipelineContext`` object itself remains mutable.
        This is safe for typical usage patterns where results are read after
        creation. For additional safety when sharing across threads:

        - **Safe**: Reading ``context.data`` from multiple threads
        - **Safe**: Passing result to read-only consumers
        - **Caution**: Modifying ``context.data`` (possible but discouraged)

    Best Practices
    --------------
    1. Treat ``context`` as read-only after pipeline execution completes
    2. Use ``frozen_context_data`` property for truly immutable access
    3. Use ``frozen_copy()`` method when sharing results across threads
    4. The defensive copy on construction protects against accidental mutation
       of the original context

    Thread-Safe API
    ---------------
    For thread-safe sharing, use the provided methods instead of manual deep copies:

    - ``frozen_context_data``: Returns MappingProxyType of deep-copied data
    - ``frozen_copy()``: Returns new result instance with deep-copied context

    Example::

        result = pipeline.execute()
        # Option 1: Get immutable data snapshot
        frozen_data = result.frozen_context_data  # MappingProxyType

        # Option 2: Get fully independent copy
        safe_result = result.frozen_copy()
        executor.submit(worker_fn, safe_result)

    Example - Defensive Copy Behavior::

        # Original context
        ctx = ModelPipelineContext(data={"key": {"nested": "value"}})

        # Create result - defensive copy is made
        result = ModelPipelineResult(success=True, context=ctx)

        # Modifying original context does NOT affect result
        ctx.data["key"]["nested"] = "modified"
        assert result.context.data["key"]["nested"] == "value"  # Unchanged!
    """

    # TODO(OMN-TBD): [pydantic-v3] Re-evaluate from_attributes=True when Pydantic v3 is released.
    # This workaround addresses Pydantic 2.x class identity validation issues where
    # frozen models (and models containing frozen nested models like ModelHookError)
    # fail isinstance() checks across pytest-xdist worker processes.
    # See model_pipeline_hook.py module docstring for detailed explanation.
    # Track: https://github.com/pydantic/pydantic/issues (no specific issue yet)  [NEEDS TICKET]
    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
        from_attributes=True,
    )

    success: bool = Field(
        ...,
        description="Whether the pipeline completed without errors",
    )
    errors: tuple[ModelHookError, ...] = Field(
        default=(),
        description=(
            "Errors captured from continue-on-error phases. "
            "THREAD SAFETY: Stored as immutable tuple of frozen ModelHookError instances. "
            "Both the tuple and its contents are immutable, making this field fully "
            "thread-safe for concurrent read access. Lists passed to the constructor "
            "are automatically converted to tuples via the _ensure_errors_immutable validator."
        ),
    )
    context: ModelPipelineContext | None = Field(
        default=None,
        description=(
            "Final context state after pipeline execution. "
            "A defensive deep copy is created on initialization to prevent "
            "external mutation of the original context passed to the constructor. "
            "THREAD SAFETY: While the result is frozen and the defensive copy breaks "
            "external references, the context object itself remains mutable. "
            "For truly thread-safe sharing: "
            "(1) Use frozen_context_data property for immutable MappingProxyType view, or "
            "(2) Use frozen_copy() method for a completely independent copy. "
            "See class docstring Thread Safety section and docs/guides/THREADING.md."
        ),
    )

    @field_validator("errors", mode="before")
    @classmethod
    def _ensure_errors_immutable(
        cls, v: Sequence[ModelHookError] | tuple[ModelHookError, ...] | None
    ) -> tuple[ModelHookError, ...]:
        """
        Convert errors to immutable tuple for thread safety.

        This validator ensures that even if a list is passed, it is converted
        to a tuple to prevent external mutation of the errors collection.
        Additionally, each error is validated to ensure it's a proper
        ModelHookError instance.

        Parameters
        ----------
        v : Sequence[ModelHookError] | tuple[ModelHookError, ...] | None
            The errors to validate. Can be a list, tuple, or None.

        Returns
        -------
        tuple[ModelHookError, ...]
            An immutable tuple of errors.
        """
        if v is None:
            return ()
        if isinstance(v, tuple):
            return v
        # Convert sequence (list, etc.) to tuple for immutability
        return tuple(v)

    @field_validator("context", mode="before")
    @classmethod
    def _create_defensive_context_copy(
        cls, v: ModelPipelineContext | Mapping[str, object] | None
    ) -> ModelPipelineContext | None:
        """
        Create a defensive deep copy of context data for thread safety.

        This validator ensures that the context's data dictionary is deep-copied
        on initialization, breaking any reference sharing with external mutable
        data structures. This prevents external code from modifying the result's
        context after creation.

        Parameters
        ----------
        v : ModelPipelineContext | Mapping[str, object] | None
            The context to validate. Can be a ModelPipelineContext instance,
            a mapping (for from_attributes compatibility), or None.

        Returns
        -------
        ModelPipelineContext | None
            A new ModelPipelineContext with deep-copied data, or None.

        Note
        ----
        The deep copy is performed on the context's ``data`` dictionary.
        The returned ModelPipelineContext is still technically mutable,
        but it no longer shares references with external data structures.
        For truly immutable access after construction, use ``frozen_context_data``
        or ``frozen_copy()``.
        """
        if v is None:
            return None

        # Handle ModelPipelineContext instance - create defensive copy
        # This is the expected case during normal pipeline execution
        if isinstance(v, ModelPipelineContext):
            return ModelPipelineContext(data=deepcopy(v.data))

        # Handle mapping input (e.g., from from_attributes or model_validate)
        # This path is used when Pydantic passes raw dict data
        raw_data = v.get("data", {})
        # Pydantic guarantees data field is a dict when present
        data: dict[str, object] = raw_data if isinstance(raw_data, dict) else {}
        return ModelPipelineContext(data=deepcopy(data))

    @property
    def frozen_context_data(self) -> Mapping[str, Any]:
        """
        Return an immutable snapshot of context data for thread-safe sharing.

        Creates a deep copy of the context data wrapped in MappingProxyType,
        making it safe to share across threads without risk of concurrent
        modification.

        Returns
        -------
        Mapping[str, Any]
            An immutable view of the context data. Returns an empty
            MappingProxyType if context is None or has no data.

        Examples
        --------
        >>> result = pipeline.execute()
        >>> # Safe to share across threads - immutable snapshot
        >>> data = result.frozen_context_data
        >>> # data["key"] = "value"  # Raises TypeError

        Note
        ----
        Each call creates a new deep copy. If you need to access the data
        multiple times, store the result in a variable.
        """
        if self.context is None:
            return MappingProxyType({})
        return MappingProxyType(deepcopy(self.context.data))

    def frozen_copy(self) -> "ModelPipelineResult":
        """
        Create a new result with frozen context data for thread-safe sharing.

        Returns a new ModelPipelineResult instance where the context contains
        a deep-copied snapshot of the original data. The new context is still
        a ModelPipelineContext (for type compatibility) but its data has been
        deep-copied to prevent accidental mutation of the original.

        This is useful when you need to:
        - Pass results to multiple concurrent consumers
        - Store results for later analysis without risk of modification
        - Create defensive copies at thread boundaries

        Returns
        -------
        ModelPipelineResult
            A new instance with deep-copied context data and copied errors tuple.

        Examples
        --------
        >>> result = pipeline.execute()
        >>> # Create frozen copy for thread-safe sharing
        >>> frozen = result.frozen_copy()
        >>> # Pass to worker threads safely
        >>> executor.submit(process_result, frozen)

        Thread Safety
        -------------
        - **errors**: Copied to new tuple (complete object isolation)
        - **context**: Deep-copied (new isolated instance per copy)
        - **success**: Shared by reference (safe - bool is immutable)

        Note
        ----
        The returned result's context is still technically mutable (it's a
        ModelPipelineContext), but modifying it won't affect the original
        result. For truly immutable access, use ``frozen_context_data``.

        Object Isolation
        ----------------
        Both errors and context are copied to new objects to ensure complete
        isolation between the original and the copy. While errors tuple and
        its frozen ModelHookError contents are inherently immutable (making
        sharing by reference technically safe), copying provides:

        1. **Cleaner semantics**: ``original.errors is not copy.errors``
        2. **Predictable identity**: Each copy has its own distinct objects
        3. **Defensive consistency**: All mutable-looking fields are copied
        """
        # Copy errors tuple for complete object isolation.
        # Note: While tuple and frozen ModelHookError contents are immutable
        # (making reference sharing technically safe), copying provides cleaner
        # semantics where each frozen copy has completely independent objects.
        # This ensures `original.errors is not copy.errors` for predictable
        # identity checks and consistent defensive copying behavior.
        #
        # IMPORTANT: We use generator expression to force a new tuple object.
        # `tuple(self.errors)` returns the same object when input is already
        # a tuple (Python optimization), but `tuple(e for e in self.errors)`
        # always creates a new tuple.
        copied_errors = tuple(e for e in self.errors)

        if self.context is None:
            return self.model_copy(update={"errors": copied_errors})

        # Deep copy context data to break reference sharing
        frozen_context = ModelPipelineContext(data=deepcopy(self.context.data))
        return self.model_copy(
            update={"context": frozen_context, "errors": copied_errors}
        )


__all__ = [
    "ModelPipelineResult",
]
