from __future__ import annotations

from datetime import datetime
from typing import Any, List, Optional

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.enums.enum_onex_status import EnumOnexStatus
from omnibase_core.model.core.model_generic_metadata import \
    ModelGenericMetadata
from omnibase_core.model.core.model_orchestrator_info import \
    ModelOrchestratorInfo

from .model_onex_message import ModelOnexMessage
from .model_unified_summary import ModelUnifiedSummary
from .model_unified_version import ModelUnifiedVersion


class ModelOnexResult(BaseModel):
    """
    Machine-consumable result for validation, tooling, or test execution.
    Supports recursive composition, extensibility, and protocol versioning.
    """

    status: EnumOnexStatus
    target: Optional[str] = Field(
        None, description="Target file or resource validated."
    )
    messages: List[ModelOnexMessage] = Field(default_factory=list)
    summary: Optional[ModelUnifiedSummary] = None
    metadata: Optional[ModelGenericMetadata] = None
    suggestions: Optional[List[str]] = None
    diff: Optional[str] = None
    auto_fix_applied: Optional[bool] = None
    fixed_files: Optional[List[str]] = None
    failed_files: Optional[List[str]] = None
    version: Optional[ModelUnifiedVersion] = None
    duration: Optional[float] = None
    exit_code: Optional[int] = None
    run_id: Optional[str] = None
    child_results: Optional[List["ModelOnexResult"]] = None
    output_format: Optional[str] = None
    cli_args: Optional[List[str]] = None
    orchestrator_info: Optional[ModelOrchestratorInfo] = None
    tool_name: Optional[str] = None
    skipped_reason: Optional[str] = None
    coverage: Optional[float] = None
    test_type: Optional[str] = None
    batch_id: Optional[str] = None
    parent_id: Optional[str] = None
    timestamp: Optional[datetime] = None
    model_config = ConfigDict(
        arbitrary_types_allowed=True,
        json_schema_extra={
            "example": {
                "status": "success",
                "run_id": "abc123",
                "tool_name": "metadata_block",
                "target": "file.yaml",
                "messages": [
                    {
                        "summary": "All required metadata fields present.",
                        "level": "info",
                    }
                ],
                "version": "v1",
            }
        },
    )

    def __init__(self, **data: Any) -> None:
        super().__init__(**data)
