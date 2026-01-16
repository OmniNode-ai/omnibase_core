"""Pipeline base exception."""

from omnibase_core.models.errors.model_onex_error import ModelOnexError


class PipelineError(ModelOnexError):
    """
    Base exception for pipeline errors.

    Thread Safety: Exception instances are thread-safe. They are effectively
    immutable after construction and can be safely raised, caught, and logged
    across threads.
    """


__all__ = ["PipelineError"]
