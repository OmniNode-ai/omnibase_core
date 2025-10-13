from pydantic import BaseModel, Field


class ModelAgentSafety(BaseModel):
    """Agent safety configuration."""

    max_file_changes: int = Field(
        description="Maximum number of files that can be modified in one operation",
    )
    max_execution_time: int = Field(description="Maximum execution time in seconds")
    require_tests: bool = Field(
        description="Whether tests are required for code changes",
    )
    auto_rollback: bool = Field(
        description="Whether to automatically rollback failed operations",
    )
    validation_timeout: int = Field(
        description="Timeout for validation operations in seconds",
    )
