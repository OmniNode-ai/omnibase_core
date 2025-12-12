"""Simple JSON data container for request bodies."""

from pydantic import BaseModel, ConfigDict


class ModelSimpleJsonData(BaseModel):
    """Typed JSON data container for request bodies.

    Simple wrapper that allows arbitrary fields for JSON data.
    This is a lightweight container for HTTP request JSON bodies,
    distinct from the complex ModelJsonData which provides full
    ONEX-compliant validation and typing.
    """

    model_config = ConfigDict(extra="allow")  # Allow arbitrary fields for JSON data


__all__ = ["ModelSimpleJsonData"]
