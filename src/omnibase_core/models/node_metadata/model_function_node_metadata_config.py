"""Configuration for ModelFunctionNodeMetadata."""

from pydantic import ConfigDict


class ModelFunctionNodeMetadataConfig:
    """Configuration for ModelFunctionNodeMetadata."""

    model_config = ConfigDict(
        extra="ignore",
        use_enum_values=False,
        validate_assignment=True,
    )
