"""
Strongly-typed Pydantic models for database operations.

Replaces Dict[str, Any] patterns in database services with proper type safety.
"""

from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, Field, field_validator


class ModelDatabaseRecord(BaseModel):
    """Model for a database record."""
    
    id: str = Field(..., description="Unique record identifier")
    table_name: str = Field(..., description="Table name")
    data: dict[str, Any] = Field(..., description="Record data")
    created_at: datetime = Field(default_factory=datetime.utcnow, description="Creation timestamp")
    updated_at: datetime = Field(default_factory=datetime.utcnow, description="Last update timestamp")
    version: int = Field(1, description="Record version for optimistic locking")
    metadata: dict[str, Any] = Field(default_factory=dict, description="Additional metadata")
    
    class Config:
        """Pydantic configuration."""
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class ModelDatabaseQuery(BaseModel):
    """Model for database query parameters."""
    
    table_name: str = Field(..., description="Table to query")
    filters: dict[str, Any] = Field(default_factory=dict, description="Query filters")
    sort_by: Optional[str] = Field(None, description="Sort field")
    sort_order: str = Field("asc", description="Sort order (asc/desc)")
    limit: Optional[int] = Field(None, description="Result limit")
    offset: int = Field(0, description="Result offset")
    projection: Optional[list[str]] = Field(None, description="Fields to include")
    
    @field_validator('sort_order')
    @classmethod
    def validate_sort_order(cls, v: str) -> str:
        """Validate sort order."""
        if v.lower() not in ['asc', 'desc']:
            raise ValueError("Sort order must be 'asc' or 'desc'")
        return v.lower()


class ModelDatabaseResult(BaseModel):
    """Model for database query results."""
    
    records: list[ModelDatabaseRecord] = Field(default_factory=list, description="Query results")
    total_count: int = Field(0, description="Total matching records")
    page_count: int = Field(0, description="Number of pages")
    current_page: int = Field(1, description="Current page number")
    query: ModelDatabaseQuery = Field(..., description="Original query")
    execution_time_ms: float = Field(0, description="Query execution time in milliseconds")
    
    def calculate_pagination(self) -> None:
        """Calculate pagination metadata."""
        if self.query.limit:
            self.page_count = (self.total_count + self.query.limit - 1) // self.query.limit
            self.current_page = (self.query.offset // self.query.limit) + 1


class ModelDatabaseTransaction(BaseModel):
    """Model for database transaction."""
    
    transaction_id: str = Field(..., description="Unique transaction identifier")
    operations: list[dict[str, Any]] = Field(default_factory=list, description="Transaction operations")
    status: str = Field("pending", description="Transaction status")
    started_at: datetime = Field(default_factory=datetime.utcnow, description="Transaction start time")
    completed_at: Optional[datetime] = Field(None, description="Transaction completion time")
    error: Optional[str] = Field(None, description="Error message if failed")
    metadata: dict[str, Any] = Field(default_factory=dict, description="Transaction metadata")
    
    @field_validator('status')
    @classmethod
    def validate_status(cls, v: str) -> str:
        """Validate transaction status."""
        valid_statuses = ['pending', 'in_progress', 'committed', 'rolled_back', 'failed']
        if v not in valid_statuses:
            raise ValueError(f"Status must be one of {valid_statuses}")
        return v


class ModelTableSchema(BaseModel):
    """Model for database table schema."""
    
    table_name: str = Field(..., description="Table name")
    columns: dict[str, str] = Field(..., description="Column name to type mapping")
    primary_key: str = Field(..., description="Primary key column")
    indexes: list[str] = Field(default_factory=list, description="Indexed columns")
    constraints: dict[str, Any] = Field(default_factory=dict, description="Table constraints")
    created_at: datetime = Field(default_factory=datetime.utcnow, description="Schema creation time")
    version: int = Field(1, description="Schema version")