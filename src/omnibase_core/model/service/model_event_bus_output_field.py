from typing import Any

from pydantic import BaseModel


class ModelEventBusOutputField(BaseModel):
    """
    Output field for event bus processing (processed, integration, backend, custom).
    """

    processed: str | None = None
    integration: bool | None = None
    backend: str
    custom: Any | None = None
