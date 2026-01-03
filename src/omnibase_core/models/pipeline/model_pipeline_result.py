# SPDX-FileCopyrightText: 2025 OmniNode Team <info@omninode.ai>
#
# SPDX-License-Identifier: Apache-2.0
"""Pipeline result model for execution outcomes."""

from collections.abc import Mapping
from copy import deepcopy
from types import MappingProxyType
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.models.pipeline.model_hook_error import ModelHookError
from omnibase_core.models.pipeline.model_pipeline_context import ModelPipelineContext


class ModelPipelineResult(BaseModel):
    """
    Result of pipeline execution.

    Contains success status, any captured errors (from continue phases),
    and the final context state.

    Thread Safety
    -------------
    **Partially thread-safe with caveats.**

    This model uses ``frozen=True``, making the result itself immutable.
    The ``errors`` field is a tuple (immutable), ensuring captured errors
    cannot be modified after creation. However, the nested ``context`` field
    (ModelPipelineContext) is intentionally mutable to allow inter-hook
    communication during pipeline execution.

    Immutable Fields
    ----------------
    - ``success``: bool (immutable by nature)
    - ``errors``: tuple of ModelHookError (immutable - safe to share)

    Mutable Fields
    --------------
    - ``context``: ModelPipelineContext (intentionally mutable for hook communication)

    .. warning:: **Mutable Context in Frozen Result**

        While ``ModelPipelineResult`` is frozen, the ``context`` field contains
        a mutable ``ModelPipelineContext`` object. This creates a thread safety
        boundary:

        - **Safe**: Reading result fields (``success``, ``errors``) across threads
        - **Safe**: Reading ``context.data`` after pipeline completion
        - **Unsafe**: Modifying ``context.data`` after sharing across threads

        If you need to share a pipeline result across threads after execution,
        create a deep copy of the context data::

            import copy

            # Safe way to share result across threads
            result = pipeline.execute()
            frozen_data = copy.deepcopy(result.context.data) if result.context else {}

    Best Practices
    --------------
    1. Treat ``context`` as read-only after pipeline execution completes
    2. Use ``frozen_context_data`` property for truly immutable access
    3. Use ``frozen_copy()`` method when sharing results across threads
    4. Do not pass the same result instance to multiple concurrent consumers
       that may modify ``context.data``

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
    """

    # TODO(pydantic-v3): Re-evaluate from_attributes=True when Pydantic v3 is released.
    # This workaround addresses Pydantic 2.x class identity validation issues where
    # frozen models (and models containing frozen nested models like ModelHookError)
    # fail isinstance() checks across pytest-xdist worker processes.
    # See model_pipeline_hook.py module docstring for detailed explanation.
    # Track: https://github.com/pydantic/pydantic/issues (no specific issue yet)
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
            "Immutable tuple for thread-safe access across concurrent consumers."
        ),
    )
    context: ModelPipelineContext | None = Field(
        default=None,
        description=(
            "Final context state after pipeline execution. "
            "WARNING: This field is mutable even though the result is frozen. "
            "Treat as read-only when sharing across threads. See class docstring."
        ),
    )

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
            A new instance with deep-copied context data.

        Examples
        --------
        >>> result = pipeline.execute()
        >>> # Create frozen copy for thread-safe sharing
        >>> frozen = result.frozen_copy()
        >>> # Pass to worker threads safely
        >>> executor.submit(process_result, frozen)

        Note
        ----
        The returned result's context is still technically mutable (it's a
        ModelPipelineContext), but modifying it won't affect the original
        result. For truly immutable access, use ``frozen_context_data``.
        """
        if self.context is None:
            return self.model_copy()

        # Deep copy context data to break reference sharing
        frozen_context = ModelPipelineContext(data=deepcopy(self.context.data))
        return self.model_copy(update={"context": frozen_context})


__all__ = [
    "ModelPipelineResult",
]
