"""
ONEX Reply Model Class.

Onex standard reply implementation with comprehensive response wrapping,
status tracking, error information, and performance metrics for ONEX tool communication.
"""

from datetime import UTC, datetime
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from pydantic import BaseModel, Field, ValidationInfo, field_validator

from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.enums.enum_onex_reply_status import EnumOnexReplyStatus
from omnibase_core.models.core.model_onex_error_details import ModelOnexErrorDetails
from omnibase_core.models.core.model_onex_performance_metrics import (
    ModelOnexPerformanceMetrics,
)
from omnibase_core.models.errors.model_onex_error import ModelOnexError
from omnibase_core.models.primitives.model_semver import ModelSemVer

if TYPE_CHECKING:
    from omnibase_core.models.protocols.protocol_onex_validation import (
        ModelOnexMetadata,
    )


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
        default_factory=lambda: datetime.now(UTC),
        description="Reply creation timestamp",
    )

    # === STATUS INFORMATION ===
    status: EnumOnexReplyStatus = Field(description="Reply status")
    success: bool = Field(description="Whether operation succeeded")

    # === DATA PAYLOAD ===
    data: BaseModel | None = Field(default=None, description="Response data")
    data_type: str | None = Field(default=None, description="Type of response data")

    # === ERROR INFORMATION ===
    error: ModelOnexErrorDetails | None = Field(
        default=None,
        description="Error details if applicable",
    )
    validation_errors: list[str] = Field(
        default_factory=list,
        description="Validation error messages",
    )

    # === ROUTING INFORMATION ===
    source_tool: str | None = Field(
        default=None,
        description="Source tool identifier",
    )
    target_tool: str | None = Field(
        default=None,
        description="Target tool identifier",
    )
    operation: str | None = Field(default=None, description="Completed operation")

    # === PERFORMANCE METRICS ===
    performance: ModelOnexPerformanceMetrics | None = Field(
        default=None,
        description="Performance metrics",
    )

    # === METADATA ===
    metadata: "ModelOnexMetadata | None" = Field(
        default=None,
        description="Additional reply metadata",
    )

    # === Onex COMPLIANCE ===
    onex_version: ModelSemVer = Field(
        ...,  # REQUIRED - specify in contract
        description="ONEX standard version",
    )
    reply_version: ModelSemVer = Field(
        ...,  # REQUIRED - specify in contract
        description="Reply schema version",
    )

    # === TRACKING INFORMATION ===
    request_id: UUID | None = Field(default=None, description="Request identifier")
    trace_id: UUID | None = Field(
        default=None,
        description="Distributed trace identifier",
    )
    span_id: UUID | None = Field(default=None, description="Trace span identifier")

    # === ADDITIONAL CONTEXT ===
    warnings: list[str] = Field(default_factory=list, description="Warning messages")
    debug_info: dict[str, str] | None = Field(
        default=None,
        description="Debug information for development",
    )

    # Config imported from model_onex_reply_config.py

    @field_validator("success")
    @classmethod
    def validate_success_consistency(
        cls,
        v: bool,
        info: ValidationInfo,
    ) -> bool:
        """Validate success field consistency with status."""
        status = info.data.get("status")
        if status == EnumOnexReplyStatus.SUCCESS:
            return True
        if status in [
            EnumOnexReplyStatus.FAILURE,
            EnumOnexReplyStatus.ERROR,
            EnumOnexReplyStatus.TIMEOUT,
            EnumOnexReplyStatus.VALIDATION_ERROR,
        ]:
            return False
        if status == EnumOnexReplyStatus.PARTIAL_SUCCESS:
            # Partial success can be either true or false depending on context
            return v
        return v

    @field_validator("data_type")
    @classmethod
    def validate_data_type_consistency(
        cls,
        v: str | None,
        info: ValidationInfo,
    ) -> str | None:
        """Validate data_type is specified when data is present."""
        data = info.data.get("data")
        if data is not None and (v is None or not v.strip()):
            msg = "data_type must be specified when data is present"
            raise ModelOnexError(
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                message=msg,
            )
        return v

    @field_validator("error")
    @classmethod
    def validate_error_consistency(
        cls,
        v: ModelOnexErrorDetails | None,
        info: ValidationInfo,
    ) -> ModelOnexErrorDetails | None:
        """Validate error details consistency with status."""
        status = info.data.get("status")
        success = info.data.get("success", True)

        if (
            not success
            and status in [EnumOnexReplyStatus.ERROR, EnumOnexReplyStatus.FAILURE]
            and v is None
        ):
            msg = "Error details must be provided for error/failure status"
            raise ModelOnexError(
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                message=msg,
            )

        return v

    @classmethod
    def create_success(
        cls,
        data: BaseModel,
        correlation_id: UUID,
        data_type: str | None = None,
        metadata: "ModelOnexMetadata | None" = None,
        performance_metrics: ModelOnexPerformanceMetrics | None = None,
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
            onex_version=ModelSemVer(major=1, minor=0, patch=0),
            reply_version=ModelSemVer(major=1, minor=0, patch=0),
        )

    @classmethod
    def create_error(
        cls,
        correlation_id: UUID,
        error_message: str,
        error_code: str | None = None,
        error_type: str = "general_error",
        additional_context: dict[str, str] | None = None,
        metadata: "ModelOnexMetadata | None" = None,
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
            onex_version=ModelSemVer(major=1, minor=0, patch=0),
            reply_version=ModelSemVer(major=1, minor=0, patch=0),
        )

    @classmethod
    def create_validation_error(
        cls,
        correlation_id: UUID,
        validation_errors: list[str],
        metadata: "ModelOnexMetadata | None" = None,
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
            onex_version=ModelSemVer(major=1, minor=0, patch=0),
            reply_version=ModelSemVer(major=1, minor=0, patch=0),
        )

    def with_metadata(self, metadata: "ModelOnexMetadata") -> "ModelOnexReply":
        """
        Add metadata to the reply.

        Args:
            metadata: Structured metadata model

        Returns:
            New reply instance with metadata
        """
        return self.model_copy(update={"metadata": metadata})

    def add_warning(self, warning: str) -> "ModelOnexReply":
        """
        Add warning to the reply.

        Args:
            warning: Warning message

        Returns:
            New reply instance with added warning
        """
        new_warnings = [*self.warnings, warning]
        return self.model_copy(update={"warnings": new_warnings})

    def with_performance_metrics(
        self,
        metrics: ModelOnexPerformanceMetrics,
    ) -> "ModelOnexReply":
        """
        Add performance metrics to the reply.

        Args:
            metrics: Performance metrics

        Returns:
            New reply instance with performance metrics
        """
        return self.model_copy(update={"performance": metrics})

    def with_routing(
        self,
        source_tool: str,
        target_tool: str,
        operation: str,
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
        return self.model_copy(
            update={
                "source_tool": source_tool,
                "target_tool": target_tool,
                "operation": operation,
            },
        )

    def with_tracing(
        self,
        trace_id: UUID,
        span_id: UUID,
        request_id: UUID | None = None,
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
        return self.model_copy(
            update={"trace_id": trace_id, "span_id": span_id, "request_id": request_id},
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

    def get_processing_time_ms(self) -> float | None:
        """Get processing time in milliseconds."""
        return self.performance.processing_time_ms if self.performance else None

    def get_error_message(self) -> str | None:
        """Get error message if present."""
        return self.error.error_message if self.error else None

    def get_error_code(self) -> str | None:
        """Get error code if present."""
        return self.error.error_code if self.error else None

    def to_dict(self) -> dict[str, str]:
        """Convert reply to dictionary representation with string values."""
        # Use model_dump() as the base for consistency
        result = self.model_dump()

        # Apply custom string formatting and transformations
        return {
            "reply_id": str(result["reply_id"]),
            "correlation_id": str(result["correlation_id"]),
            "timestamp": (
                result["timestamp"].isoformat()
                if isinstance(result["timestamp"], datetime)
                else str(result["timestamp"])
            ),
            "status": result["status"],
            "success": str(result["success"]),
            "data": str(self.data.model_dump()) if self.data else "",
            "data_type": result.get("data_type") or "",
            "error": str(self.error.model_dump()) if self.error else "",
            "validation_errors": str(result["validation_errors"]),
            "source_tool": result.get("source_tool") or "",
            "target_tool": result.get("target_tool") or "",
            "operation": result.get("operation") or "",
            "performance": (
                str(self.performance.model_dump()) if self.performance else ""
            ),
            "metadata": str(self.metadata.model_dump()) if self.metadata else "",
            "onex_version": str(self.onex_version.model_dump()),
            "reply_version": str(self.reply_version.model_dump()),
            "request_id": result.get("request_id") or "",
            "trace_id": result.get("trace_id") or "",
            "span_id": result.get("span_id") or "",
            "warnings": str(result["warnings"]),
            "debug_info": str(result.get("debug_info")) if self.debug_info else "",
        }

    def get_age_seconds(self) -> float:
        """Get age of reply in seconds."""
        return (datetime.now(UTC) - self.timestamp).total_seconds()

    def get_summary(self) -> str:
        """Get a human-readable summary of the reply."""
        if self.is_success():
            return f"Success: {self.data_type or 'data'} returned"
        elif self.is_error():
            return f"Error: {self.get_error_message() or 'Unknown error'}"
        else:
            return f"Status: {self.status.value}"
