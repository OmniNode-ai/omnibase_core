"""Configuration for ModelSecureEventEnvelope.

Provides configuration settings for secure event envelope behavior,
including validation and serialization options.

Note:
    This module provides a recommended ConfigDict constant for secure event
    envelope models. Models should apply this config directly rather than
    inheriting from a non-Pydantic class (which doesn't work with Pydantic's
    config inheritance mechanism).
"""

from pydantic import ConfigDict

# Recommended ConfigDict for secure event envelope Pydantic models.
#
# Key settings:
# - from_attributes=True: Supports pytest-xdist parallel execution where
#   class identity may differ between workers.
# - frozen=True: Enforces immutability for security-critical models.
# - extra="forbid": Prevents injection of unexpected fields.
#
# Usage:
#     class MySecureModel(BaseModel):
#         model_config = SECURE_EVENT_ENVELOPE_CONFIG
#
SECURE_EVENT_ENVELOPE_CONFIG: ConfigDict = ConfigDict(
    from_attributes=True,
    frozen=True,
    extra="forbid",
)


class ModelSecureEventEnvelopeConfig:
    """Deprecated configuration class - use SECURE_EVENT_ENVELOPE_CONFIG instead.

    .. deprecated::
        This class is deprecated. Use SECURE_EVENT_ENVELOPE_CONFIG constant
        directly in your Pydantic model's model_config instead.

    Important:
        Non-Pydantic classes cannot provide inheritable ConfigDict settings
        to Pydantic models. Each Pydantic model must define its own
        model_config. This class is retained as a deprecated alias.

    Note:
        This model uses from_attributes=True to support pytest-xdist parallel
        execution where class identity may differ between workers.
    """

    model_config = ConfigDict(from_attributes=True, frozen=True, extra="forbid")
