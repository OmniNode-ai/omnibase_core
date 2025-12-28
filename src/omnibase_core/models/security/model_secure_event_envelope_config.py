"""Configuration for ModelSecureEventEnvelope.

Provides configuration settings for secure event envelope behavior,
including validation and serialization options.
"""

from pydantic import ConfigDict


class ModelSecureEventEnvelopeConfig:
    """Configuration class for ModelSecureEventEnvelope behavior.

    This class provides shared configuration for secure event envelope
    Pydantic models. It is not itself a Pydantic model but provides
    ConfigDict settings for models that inherit from it.

    Note:
        This model uses from_attributes=True to support pytest-xdist parallel
        execution where class identity may differ between workers.
    """

    model_config = ConfigDict(from_attributes=True)
