"""
Cache state models for OmniMemory system.

Represents various cache structures used internally by services.
"""

from datetime import datetime
from typing import Dict, Optional

from pydantic import BaseModel, Field


class ModelFileState(BaseModel):
    """Represents the state of a monitored file."""

    mtime: float = Field(..., description="Modification time of the file")
    size: int = Field(..., description="Size of the file in bytes")
    content_hash: str = Field(..., description="Hash of the file content")
    last_checked: datetime = Field(
        default_factory=datetime.utcnow, description="Last time the file was checked"
    )


class ModelPatternCache(BaseModel):
    """Represents compiled regex pattern cache."""

    patterns: Dict[str, str] = Field(
        default_factory=dict, description="Map of pattern ID to regex pattern string"
    )

    # Note: We can't serialize compiled re.Pattern objects directly
    # The service will need to compile these at runtime


class ModelASTCache(BaseModel):
    """Represents parsed AST cache entry."""

    cache_key: str = Field(..., description="Unique cache key")
    file_path: Optional[str] = Field(None, description="Source file path")
    code_hash: str = Field(..., description="Hash of the code")
    parsed_at: datetime = Field(
        default_factory=datetime.utcnow, description="When the code was parsed"
    )
    # AST objects can't be serialized directly - store as string representation
    ast_repr: str = Field(..., description="String representation of the AST")


class ModelPerformanceCache(BaseModel):
    """Represents performance metrics cache."""

    rule_id: str = Field(..., description="Rule identifier")
    average_execution_time_ms: float = Field(
        ..., description="Average execution time in milliseconds"
    )
    last_execution_time_ms: float = Field(
        ..., description="Last execution time in milliseconds"
    )
    execution_count: int = Field(default=1, description="Number of executions")
    last_executed: datetime = Field(
        default_factory=datetime.utcnow, description="Last execution timestamp"
    )
