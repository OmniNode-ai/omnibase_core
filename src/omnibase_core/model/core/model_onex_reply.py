"""
ONEX Reply Model Implementation

Pydantic model implementing the ONEX standard reply pattern.
Provides response wrapping with status, data, and error information.
"""

from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional, Union
from uuid import UUID, uuid4

from pydantic import BaseModel, Field, validator

from omnibase_core.model.core.model_semver import ModelSemVer

from ..protocols.protocol_onex_validation import ModelOnexMetadata


class EnumOnexReplyStatus(str, Enum):
    """Standard ONEX reply status values."""

    SUCCESS = "success"
    PARTIAL_SUCCESS = "partial_success"
    FAILURE = "failure"
    ERROR = "error"
    TIMEOUT = "timeout"
    VALIDATION_ERROR = "validation_error"


class ModelOnexErrorDetails(BaseModel):
    """Detailed error information for Onex replies."""

    error_code: str = Field(description="Machine-readable error code")
    error_message: str = Field(description="Human-readable error message")
    error_type: str = Field(description="Error classification")
    stack_trace: Optional[str] = Field(
        default=None, description="Stack trace if available"
    )
    additional_context: Dict[str, str] = Field(
        default_factory=dict, description="Additional error context"
    )
    resolution_suggestions: List[str] = Field(
        default_factory=list, description="Suggested resolution steps"
    )

    class Config:
        frozen = True


class ModelOnexPerformanceMetrics(BaseModel):
    """Performance metrics for Onex replies."""

    processing_time_ms: float = Field(description="Processing time in milliseconds")
    queue_time_ms: Optional[float] = Field(
        default=None, description="Queue time in milliseconds"
    )
    network_time_ms: Optional[float] = Field(
        default=None, description="Network time in milliseconds"
    )
    memory_usage_mb: Optional[float] = Field(
        default=None, description="Memory usage in MB"
    )
    cpu_usage_percent: Optional[float] = Field(
        default=None, description="CPU usage percentage"
    )

    class Config:
        frozen = True


class ModelOnexReply(BaseModel):
    """
    Onex standard reply implementation.

    Wraps response data with standardized status, error information,
    and performance metrics for ONEX tool communication.
    """

    # === CORE REPLY FIELDS ===
    reply_id: UUID = Field(default_factory=uuid4, description="Unique reply identifier")
    correlation_id: UUID = Field(description="Request correlation identifier")
    timestamp: datetime = Field(
        default_factory=datetime.utcnow, description="Reply creation timestamp"
    )

    # === STATUS INFORMATION ===
    status: EnumOnexReplyStatus = Field(description="Reply status")
    success: bool = Field(description="Whether operation succeeded")

    # === DATA PAYLOAD ===
    data: Optional[BaseModel] = Field(default=None, description="Response data")
    data_type: Optional[str] = Field(default=None, description="Type of response data")

    # === ERROR INFORMATION ===
    error: Optional[ModelOnexErrorDetails] = Field(
        default=None, description="Error details if applicable"
    )
    validation_errors: List[str] = Field(
        default_factory=list, description="Validation error messages"
    )

    # === ROUTING INFORMATION ===
    source_tool: Optional[str] = Field(
        default=None, description="Source tool identifier"
    )
    target_tool: Optional[str] = Field(
        default=None, description="Target tool identifier"
    )
    operation: Optional[str] = Field(default=None, description="Completed operation")

    # === PERFORMANCE METRICS ===
    performance: Optional[ModelOnexPerformanceMetrics] = Field(
        default=None, description="Performance metrics"
    )

    # === METADATA ===
    metadata: Optional[ModelOnexMetadata] = Field(
        default=None, description="Additional reply metadata"
    )

    # === Onex COMPLIANCE ===
    onex_version: ModelSemVer = Field(
        default_factory=lambda: ModelSemVer(major=1, minor=0, patch=0),
        description="ONEX standard version",
    )
    reply_version: ModelSemVer = Field(
        default_factory=lambda: ModelSemVer(major=1, minor=0, patch=0),
        description="Reply schema version",
    )

    # === TRACKING INFORMATION ===
    request_id: Optional[str] = Field(default=None, description="Request identifier")
    trace_id: Optional[str] = Field(
        default=None, description="Distributed trace identifier"
    )
    span_id: Optional[str] = Field(default=None, description="Trace span identifier")

    # === ADDITIONAL CONTEXT ===
    warnings: List[str] = Field(default_factory=list, description="Warning messages")
    debug_info: Optional[Dict[str, str]] = Field(
        default=None, description="Debug information for development"
    )

    class Config:
        """Pydantic configuration."""

        frozen = True
        use_enum_values = True
        json_encoders = {UUID: str, datetime: lambda v: v.isoformat()}

    @validator("success", always=True)
    def validate_success_consistency(
        cls, v: bool, values: Dict[str, Union[bool, str, ModelOnexErrorDetails]]
    ) -> bool:
        """Validate success field consistency with status."""
        status = values.get("status")
        if status == EnumOnexReplyStatus.SUCCESS:
            return True
        elif status in [
            EnumOnexReplyStatus.FAILURE,
            EnumOnexReplyStatus.ERROR,
            EnumOnexReplyStatus.TIMEOUT,
            EnumOnexReplyStatus.VALIDATION_ERROR,
        ]:
            return False
        elif status == EnumOnexReplyStatus.PARTIAL_SUCCESS:
            # Partial success can be either true or false depending on context
            return v
        return v

    @validator("data_type")
    def validate_data_type_consistency(
        cls, v: Optional[str], values: Dict[str, Union[str, BaseModel]]
    ) -> Optional[str]:
        """Validate data_type is specified when data is present."""
        data = values.get("data")
        if data is not None and (v is None or not v.strip()):
            raise ValueError("data_type must be specified when data is present")
        return v

    @validator("error")
    def validate_error_consistency(
        cls, v: Optional[ModelOnexErrorDetails], values: Dict[str, Union[bool, str]]
    ) -> Optional[ModelOnexErrorDetails]:
        """Validate error details consistency with status."""
        status = values.get("status")
        success = values.get("success", True)

        if (
            not success
            and status in [EnumOnexReplyStatus.ERROR, EnumOnexReplyStatus.FAILURE]
            and v is None
        ):
            raise ValueError("Error details must be provided for error/failure status")

        return v

    @classmethod
    def create_success(
        cls,
        data: BaseModel,
        correlation_id: UUID,
        data_type: Optional[str] = None,
        metadata: Optional[ModelOnexMetadata] = None,
        performance_metrics: Optional[ModelOnexPerformanceMetrics] = None,
    ) -> "ModelOnexReply":
        """
        Create a successful Onex reply.

        Args:
            data: Response data
            correlation_id: Request correlation ID
            data_type: Type of response data
            metadata: Additional metadata
            performance_metrics: Performance metrics

        Returns:
            Onex reply indicating success
        """
        return cls(
            correlation_id=correlation_id,
            status=EnumOnexReplyStatus.SUCCESS,
            success=True,
            data=data,
            data_type=data_type or str(type(data).__name__),
            metadata=metadata,
            performance=performance_metrics,
        )

    @classmethod
    def create_error(
        cls,
        correlation_id: UUID,
        error_message: str,
        error_code: Optional[str] = None,
        error_type: str = "general_error",
        additional_context: Optional[Dict[str, str]] = None,
        metadata: Optional[ModelOnexMetadata] = None,
    ) -> "ModelOnexReply":
        """
        Create an error Onex reply.

        Args:
            correlation_id: Request correlation ID
            error_message: Human-readable error message
            error_code: Machine-readable error code
            error_type: Error classification
            additional_context: Additional error context
            metadata: Additional metadata

        Returns:
            Onex reply indicating error
        """
        error_details = ModelOnexErrorDetails(
            error_code=error_code or "UNKNOWN_ERROR",
            error_message=error_message,
            error_type=error_type,
            additional_context=additional_context or {},
        )

        return cls(
            correlation_id=correlation_id,
            status=EnumOnexReplyStatus.ERROR,
            success=False,
            error=error_details,
            metadata=metadata,
        )

    @classmethod
    def create_validation_error(
        cls,
        correlation_id: UUID,
        validation_errors: List[str],
        metadata: Optional[ModelOnexMetadata] = None,
    ) -> "ModelOnexReply":
        """
        Create a validation error Onex reply.

        Args:
            correlation_id: Request correlation ID
            validation_errors: List of validation error messages
            metadata: Additional metadata

        Returns:
            Onex reply indicating validation error
        """
        return cls(
            correlation_id=correlation_id,
            status=EnumOnexReplyStatus.VALIDATION_ERROR,
            success=False,
            validation_errors=validation_errors,
            metadata=metadata,
        )

    def with_metadata(self, metadata: ModelOnexMetadata) -> "ModelOnexReply":
        """
        Add metadata to the reply.

        Args:
            metadata: Structured metadata model

        Returns:
            New reply instance with metadata
        """
        return self.copy(update={"metadata": metadata})

    def add_warning(self, warning: str) -> "ModelOnexReply":
        """
        Add warning to the reply.

        Args:
            warning: Warning message

        Returns:
            New reply instance with added warning
        """
        new_warnings = [*self.warnings, warning]
        return self.copy(update={"warnings": new_warnings})

    def with_performance_metrics(
        self, metrics: ModelOnexPerformanceMetrics
    ) -> "ModelOnexReply":
        """
        Add performance metrics to the reply.

        Args:
            metrics: Performance metrics

        Returns:
            New reply instance with performance metrics
        """
        return self.copy(update={"performance": metrics})

    def with_routing(
        self, source_tool: str, target_tool: str, operation: str
    ) -> "ModelOnexReply":
        """
        Add routing information to the reply.

        Args:
            source_tool: Source tool identifier
            target_tool: Target tool identifier
            operation: Completed operation

        Returns:
            New reply instance with routing information
        """
        return self.copy(
            update={
                "source_tool": source_tool,
                "target_tool": target_tool,
                "operation": operation,
            }
        )

    def with_tracing(
        self, trace_id: str, span_id: str, request_id: Optional[str] = None
    ) -> "ModelOnexReply":
        """
        Add distributed tracing information to the reply.

        Args:
            trace_id: Distributed trace identifier
            span_id: Trace span identifier
            request_id: Optional request identifier

        Returns:
            New reply instance with tracing information
        """
        return self.copy(
            update={"trace_id": trace_id, "span_id": span_id, "request_id": request_id}
        )

    def is_success(self) -> bool:
        """Check if reply indicates success."""
        return self.success and self.status == EnumOnexReplyStatus.SUCCESS

    def is_error(self) -> bool:
        """Check if reply indicates error."""
        return not self.success and self.status in [
            EnumOnexReplyStatus.ERROR,
            EnumOnexReplyStatus.FAILURE,
            EnumOnexReplyStatus.VALIDATION_ERROR,
        ]

    def has_data(self) -> bool:
        """Check if reply contains data."""
        return self.data is not None

    def has_warnings(self) -> bool:
        """Check if reply contains warnings."""
        return len(self.warnings) > 0

    def get_processing_time_ms(self) -> Optional[float]:
        """Get processing time in milliseconds."""
        return self.performance.processing_time_ms if self.performance else None

    def get_error_message(self) -> Optional[str]:
        """Get error message if present."""
        return self.error.error_message if self.error else None

    def get_error_code(self) -> Optional[str]:
        """Get error code if present."""
        return self.error.error_code if self.error else None

    def to_dict(self) -> Dict[str, str]:
        """Convert reply to dictionary representation."""
        return {
            "reply_id": str(self.reply_id),
            "correlation_id": str(self.correlation_id),
            "timestamp": self.timestamp.isoformat(),
            "status": self.status,
            "success": str(self.success),
            "data": str(self.data.dict()) if self.data else "",
            "data_type": self.data_type or "",
            "error": str(self.error.dict()) if self.error else "",
            "validation_errors": str(self.validation_errors),
            "source_tool": self.source_tool or "",
            "target_tool": self.target_tool or "",
            "operation": self.operation or "",
            "performance": str(self.performance.dict()) if self.performance else "",
            "metadata": str(self.metadata.dict()) if self.metadata else "",
            "onex_version": str(self.onex_version.dict()),
            "reply_version": str(self.reply_version.dict()),
            "request_id": self.request_id or "",
            "trace_id": self.trace_id or "",
            "span_id": self.span_id or "",
            "warnings": str(self.warnings),
            "debug_info": str(self.debug_info) if self.debug_info else "",
        }
