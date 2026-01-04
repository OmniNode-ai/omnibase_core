from __future__ import annotations

import json
from typing import TYPE_CHECKING

from pydantic import BaseModel, Field

if TYPE_CHECKING:
    from omnibase_core.enums.enum_onex_status import EnumOnexStatus
    from omnibase_core.models.core.model_protocol_metadata import ModelGenericMetadata

    from .model_onex_message import ModelOnexMessage
    from .model_onex_result import ModelOnexResult
    from .model_unified_run_metadata import ModelUnifiedRunMetadata
    from .model_unified_summary import ModelUnifiedSummary
    from .model_unified_version import ModelUnifiedVersion


class ModelOnexBatchResult(BaseModel):
    """
    Batch result model for multiple OnexResult objects
    """

    results: list[ModelOnexResult]
    messages: list[ModelOnexMessage] = Field(default_factory=list)
    summary: ModelUnifiedSummary | None = None
    status: EnumOnexStatus | None = None
    version: ModelUnifiedVersion | None = None
    run_metadata: ModelUnifiedRunMetadata | None = None
    metadata: ModelGenericMetadata | None = None

    @classmethod
    def export_schema(cls) -> str:
        """Export the JSONSchema for ModelOnexBatchResult and all submodels."""
        from omnibase_core.enums.enum_log_level import EnumLogLevel as LogLevel
        from omnibase_core.logging.logging_structured import emit_log_event_sync

        emit_log_event_sync(
            LogLevel.DEBUG,
            "export_schema called",
            {"node_id": "model_onex_batch_result", "event_bus": None},
        )
        return json.dumps(cls.model_json_schema(), indent=2)
