from typing import Annotated

from pydantic import Field

from omnibase_core.models.operations.model_error_event_data import ModelErrorEventData
from omnibase_core.models.operations.model_system_event_data import ModelSystemEventData
from omnibase_core.models.operations.model_user_event_data import ModelUserEventData
from omnibase_core.models.operations.model_workflow_event_data import (
    ModelWorkflowEventData,
)

EventDataUnion = Annotated[
    ModelSystemEventData
    | ModelUserEventData
    | ModelWorkflowEventData
    | ModelErrorEventData,
    Field(discriminator="event_type"),
]
