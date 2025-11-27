from uuid import UUID

from omnibase_core.models.core.model_base_result import ModelBaseResult


class ModelWorkflowStatusResult(ModelBaseResult):
    workflow_id: UUID
    status: str
    progress: int | None = None
