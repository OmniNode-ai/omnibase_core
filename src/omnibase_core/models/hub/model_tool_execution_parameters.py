"""
ONEX-compliant model for tool execution parameters.

Replaces Dict[str, Any] with strongly typed Pydantic model following ONEX standards.
"""

from pydantic import BaseModel, Field


class ModelToolExecutionParameters(BaseModel):
    """
    Tool execution parameters model for hub tool invocation.

    Replaces Dict[str, Any] usage with strongly typed ONEX-compliant structure.
    Note: Uses Union types for parameter values to maintain flexibility while avoiding Any.
    """

    tool_name: str = Field(..., description="Name of tool to execute")
    input_parameters: dict[str, str | int | float | bool | list | dict] = Field(
        default_factory=dict,
        description="Tool input parameters with strongly typed values",
    )
    execution_timeout: int | None = Field(
        60,
        description="Execution timeout in seconds",
    )
    priority: int = Field(1, description="Execution priority (1=highest, 10=lowest)")
    correlation_id: str | None = Field(
        None,
        description="Request correlation identifier",
    )
    session_id: str | None = Field(None, description="Session identifier")
    callback_url: str | None = Field(
        None,
        description="Callback URL for async results",
    )

    class Config:
        """Pydantic configuration."""

        json_schema_extra = {
            "example": {
                "tool_name": "tool_document_processor",
                "input_parameters": {
                    "document_path": "/path/to/document.pdf",
                    "output_format": "markdown",
                    "extract_images": True,
                    "max_pages": 50,
                    "quality_settings": {"resolution": "high", "compression": False},
                },
                "execution_timeout": 300,
                "priority": 1,
                "correlation_id": "req_123456",
                "session_id": "session_abc",
                "callback_url": "https://api.example.com/callbacks/results",
            },
        }
