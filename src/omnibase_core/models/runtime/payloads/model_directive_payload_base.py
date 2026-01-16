"""
Base class for runtime directive payloads.

This module provides the foundation for typed directive payloads used by
ModelRuntimeDirective. Each directive type (SCHEDULE_EFFECT, ENQUEUE_HANDLER,
RETRY_WITH_BACKOFF, DELAY_UNTIL, CANCEL_EXECUTION) has a corresponding payload
model that inherits from this base.

Design Principles:
    - Frozen (immutable after creation) for thread safety
    - Extra fields forbidden for strict schema validation
    - All concrete payloads use a `kind` discriminator field

See Also:
    - model_directive_payloads.py: Concrete payload implementations
    - model_directive_payload_union.py: Discriminated union type
    - omnibase_core.enums.enum_directive_type: Directive type enumeration
"""

from pydantic import BaseModel, ConfigDict

__all__ = ["ModelDirectivePayloadBase"]


class ModelDirectivePayloadBase(BaseModel):
    """
    Base class for all directive payloads.

    All directive-specific payload models inherit from this base class,
    ensuring consistent configuration and behavior across payload types.

    Thread Safety:
        This model is frozen (immutable) after creation, making it safe
        to share across threads without synchronization.

    Configuration:
        - frozen=True: Immutable after creation
        - extra="forbid": No additional fields allowed
        - from_attributes=True: Allows instantiation from arbitrary objects
          (useful for pytest-xdist parallel execution)
    """

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)
