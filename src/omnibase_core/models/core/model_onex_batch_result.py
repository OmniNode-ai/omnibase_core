# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

from __future__ import annotations

import json

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.enums.enum_onex_status import EnumOnexStatus
from omnibase_core.models.core.model_protocol_metadata import ModelGenericMetadata
from omnibase_core.models.results.model_onex_message import ModelOnexMessage
from omnibase_core.models.results.model_onex_result import ModelOnexResult
from omnibase_core.models.results.model_unified_summary import ModelUnifiedSummary
from omnibase_core.models.results.model_unified_version import ModelUnifiedVersion

from .model_unified_run_metadata import ModelUnifiedRunMetadata


class ModelOnexBatchResult(BaseModel):
    """
    Batch result model for multiple OnexResult objects
    """

    model_config = ConfigDict(extra="forbid")

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
        from omnibase_core.utils.util_stdlib_log_emit import (
            emit_log_event_stdlib as emit_log_event_sync,
        )

        emit_log_event_sync(
            LogLevel.DEBUG,
            "export_schema called",
            {"node_id": "model_onex_batch_result", "event_bus": None},
        )
        return json.dumps(cls.model_json_schema(), indent=2)
