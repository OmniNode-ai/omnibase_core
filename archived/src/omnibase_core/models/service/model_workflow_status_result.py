from omnibase_core.models.core.model_base_result import ModelBaseResult


class ModelWorkflowStatusResult(ModelBaseResult):
    workflow_id: str
    status: str
    progress: int | None = None
