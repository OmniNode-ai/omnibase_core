"""Pipeline hook model.

Note: This module was moved from omnibase_core.pipeline.models to
omnibase_core.models.pipeline to comply with ONEX repository structure
validation that requires all models in src/omnibase_core/models/.

Pydantic Configuration Notes
----------------------------
All pipeline models in this module use ``from_attributes=True`` in their ConfigDict.
This addresses a specific Pydantic validation behavior with pytest-xdist parallel
test execution:

**Problem (Pydantic 2.x class identity validation):**

When pytest-xdist runs tests in parallel worker processes, each worker imports
Python classes independently. This causes the same class (e.g., ModelPipelineHook)
to have different identity in different workers::

    # Worker 1 imports ModelPipelineHook -> id(class) = 0x1234
    # Worker 2 imports ModelPipelineHook -> id(class) = 0x5678

Pydantic's default validation uses ``isinstance()`` checks, which compare class
identity. When a model instance created in one context is validated in another
(e.g., passed through multiprocessing or serialization boundaries), the
``isinstance()`` check fails even though the instance has the correct structure::

    # This fails without from_attributes=True:
    hook = ModelPipelineHook(...)  # Created with class id=0x1234
    # Later, in different import context:
    ModelExecutionPlan(phases={"before": plan_with_hook})  # Validation uses class id=0x5678
    # Pydantic rejects: isinstance(hook, ModelPipelineHook) -> False

**Solution (from_attributes=True):**

Setting ``from_attributes=True`` enables ORM-style attribute extraction. Instead
of relying on ``isinstance()`` checks, Pydantic extracts attribute values from
the object and constructs a new instance. This works regardless of class identity::

    # With from_attributes=True:
    hook = ModelPipelineHook(...)  # Created with any class identity
    # Pydantic reads hook.hook_name, hook.phase, etc. and creates new instance
    # Works even when class identity differs

**When this pattern is needed:**

- Frozen Pydantic models nested inside other Pydantic models
- Models used in pytest-xdist parallel test execution
- Models passed through multiprocessing boundaries
- Models loaded from different import contexts (e.g., dynamic imports)

**References:**

- Pydantic docs: https://docs.pydantic.dev/latest/concepts/models/#model-config
- CLAUDE.md section "Pydantic from_attributes=True for Value Objects"
- docs/conventions/PYDANTIC_BEST_PRACTICES.md

.. note::
    This workaround may become unnecessary in future Pydantic versions if they
    implement identity-agnostic validation for frozen models. See TODO comments
    in ConfigDict definitions.
"""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from omnibase_core.enums.enum_handler_type_category import EnumHandlerTypeCategory

# Canonical phase type
PipelinePhase = Literal[  # enum-ok: model type annotation
    "preflight", "before", "execute", "after", "emit", "finalize"
]


class ModelPipelineHook(BaseModel):
    """
    Represents a registered hook in the pipeline execution system.

    Hooks are registered for specific phases and ordered by dependencies
    and priority within each phase.

    Thread Safety: This class is thread-safe. Instances are immutable
    (frozen=True) and can be safely shared across threads.
    """

    # TODO(OMN-TBD): [pydantic-v3] Re-evaluate from_attributes=True when Pydantic v3 is released.
    # This workaround addresses pytest-xdist class identity issues where frozen models
    # nested in other models fail isinstance() validation across worker processes.
    # If Pydantic v3 implements identity-agnostic validation for frozen models, this
    # override may no longer be necessary. Track: https://github.com/pydantic/pydantic/issues
    # See module docstring for detailed explanation of the issue and solution.  [NEEDS TICKET]
    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
        from_attributes=True,
    )

    hook_name: str = Field(
        ...,
        min_length=1,
        description="Unique identifier for this hook",
    )
    phase: PipelinePhase = Field(
        ...,
        description="Pipeline phase where this hook executes",
    )
    handler_type_category: EnumHandlerTypeCategory | None = Field(
        default=None,
        description="Optional type category for validation. None = generic hook (allowed everywhere)",
    )
    priority: int = Field(
        default=100,
        ge=0,
        description="Execution priority within phase. Lower = earlier. Default 100.",
    )
    dependencies: list[str] = Field(
        default_factory=list,
        description="List of hook names that must execute before this hook",
    )
    callable_ref: str = Field(
        ...,
        min_length=1,
        description="Module path or registry key for the hook callable (NOT raw callable)",
    )
    timeout_seconds: float | None = Field(
        default=None,
        gt=0,
        description="Optional timeout for hook execution in seconds",
    )

    @field_validator("hook_name")
    @classmethod
    def validate_hook_name(cls, v: str) -> str:
        """Ensure hook_name is a valid identifier."""
        if not v.replace("_", "").replace("-", "").isalnum():
            # error-ok: Pydantic field_validator requires ValueError
            raise ValueError(
                f"hook_name must be alphanumeric with underscores/hyphens: {v}"
            )
        return v

    @field_validator("dependencies")
    @classmethod
    def validate_dependencies(cls, v: list[str]) -> list[str]:
        """Ensure no duplicate dependencies."""
        if len(v) != len(set(v)):
            # error-ok: Pydantic field_validator requires ValueError
            raise ValueError("Duplicate dependencies not allowed")
        return v


__all__ = [
    "ModelPipelineHook",
    "PipelinePhase",
]
