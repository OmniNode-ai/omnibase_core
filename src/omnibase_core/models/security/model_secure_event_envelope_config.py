"""Configuration for ModelSecureEventEnvelope."""

from pydantic import ConfigDict


class ModelSecureEventEnvelopeConfig:
    """Configuration for ModelSecureEventEnvelope."""

    model_config = ConfigDict(json_encoders={datetime: lambda v: v.isoformat()})
