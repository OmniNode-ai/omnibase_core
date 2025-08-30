from typing import Any, Optional

from pydantic import BaseModel


class ModelEventBusOutputField(BaseModel):
    """
    Output field for event bus processing (processed, integration, backend, custom).
    """

    processed: Optional[str] = None
    integration: Optional[bool] = None
    backend: str
    custom: Optional[Any] = None
