from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.enums.enum_onex_status import EnumOnexStatus
from omnibase_core.models.core.model_orchestrator_info import ModelOrchestratorInfo
from omnibase_core.models.core.model_protocol_metadata import ModelGenericMetadata

from .model_onex_message import ModelOnexMessage
from .model_unified_summary import ModelUnifiedSummary
from .model_unified_version import ModelUnifiedVersion


class ModelOnexResult(BaseModel):
    """
    Machine-consumable result for validation, tooling, or test execution.
    Supports recursive composition, extensibility, and protocol versioning.
    """

    status: EnumOnexStatus
    target: str | None = Field(
        default=None,
        description="Target file or resource validated.",
    )
    messages: list[ModelOnexMessage] = Field(default_factory=list)
    summary: ModelUnifiedSummary | None = None
    metadata: ModelGenericMetadata | None = None
    suggestions: list[str] | None = None
    diff: str | None = None
    auto_fix_applied: bool | None = None
    fixed_files: list[str] | None = None
    failed_files: list[str] | None = None
    version: ModelUnifiedVersion | None = None
    duration: float | None = None
    exit_code: int | None = None
    run_id: UUID | None = None
    child_results: list[ModelOnexResult] | None = None
    output_format: str | None = None
    cli_args: list[str] | None = None
    orchestrator_info: ModelOrchestratorInfo | None = None
    tool_name: str | None = None
    skipped_reason: str | None = None
    coverage: float | None = None
    test_type: str | None = None
    batch_id: UUID | None = None
    parent_id: UUID | None = None
    timestamp: datetime | None = None
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
                    },
                ],
                "version": "v1",
            },
        },
    )

    def __init__(self, **data: Any) -> None:
        super().__init__(**data)
