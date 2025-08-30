from __future__ import annotations

import json
from typing import List, Optional

from pydantic import BaseModel, Field

from omnibase_core.enums.enum_onex_status import EnumOnexStatus
from omnibase_core.model.core.model_generic_metadata import \
    ModelGenericMetadata

from .model_onex_message import ModelOnexMessage
from .model_onex_result import ModelOnexResult
from .model_unified_run_metadata import ModelUnifiedRunMetadata
from .model_unified_summary import ModelUnifiedSummary
from .model_unified_version import ModelUnifiedVersion


class ModelOnexBatchResult(BaseModel):
    """
    Batch result model for multiple OnexResult objects
    """

    results: List[ModelOnexResult]
    messages: List[ModelOnexMessage] = Field(default_factory=list)
    summary: Optional[ModelUnifiedSummary] = None
    status: Optional[EnumOnexStatus] = None
    version: Optional[ModelUnifiedVersion] = None
    run_metadata: Optional[ModelUnifiedRunMetadata] = None
    metadata: Optional[ModelGenericMetadata] = None

    @classmethod
    def export_schema(cls) -> str:
        """Export the JSONSchema for ModelOnexBatchResult and all submodels."""
        from omnibase.enums.enum_log_level import LogLevelEnum

        from omnibase_core.core.core_structured_logging import \
            emit_log_event_sync

        emit_log_event_sync(
            LogLevelEnum.DEBUG,
            "export_schema called",
            node_id="model_onex_batch_result",
            event_bus=None,  # Will be injected properly
        )
        return json.dumps(cls.model_json_schema(), indent=2)
