import uuid
from typing import Any, Optional

from pydantic import Field

"""
Internal Processing Context Model for ONEX.

This model provides a clean context for internal processing operations
where all traceability information is guaranteed to be present.
"""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel

from omnibase_core.utils.uuid_service import ServiceUUID


class ModelOnexInternalProcessingContext(BaseModel):
    """
    Internal processing context with required UUIDs for ONEX operations.

    This model provides a clean context for internal processing operations
    where all traceability information is guaranteed to be present.

    Use this for passing context between internal functions without null checking.
    """

    # Required traceability fields
    correlation_id: UUID = Field(
        default=...,
        description="Required correlation ID for tracking",
    )
    event_id: UUID = Field(default=..., description="Required event ID for tracking")
    session_id: UUID = Field(
        default=..., description="Required session ID for tracking"
    )

    # Processing metadata
    node_name: str = Field(default=..., description="Node performing the processing")
    operation: str = Field(default=..., description="Operation being performed")
    timestamp: datetime = Field(
        default_factory=datetime.utcnow,
        description="Processing timestamp",
    )

    # Optional context data
    additional_data: dict[str, Any] = Field(
        default_factory=dict,
        description="Additional processing data",
    )

    @classmethod
    def create_for_operation(
        cls,
        operation: str,
        node_name: str,
        correlation_id: UUID | None = None,
        event_id: UUID | None = None,
        session_id: UUID | None = None,
        **additional_data: Any,
    ) -> "ModelOnexInternalProcessingContext":
        """
        Create processing context for an operation, generating UUIDs as needed.

        Args:
            operation: Name of the operation being performed
            node_name: Name of the node performing the operation
            correlation_id: Optional correlation ID (generated if not provided)
            event_id: Optional event ID (generated if not provided)
            session_id: Optional session ID (generated if not provided)
            **additional_data: Additional data to include in context

        Returns:
            ModelOnexInternalProcessingContext: Context with all required UUIDs populated
        """
        return cls(
            correlation_id=correlation_id or ServiceUUID.generate_correlation_id(),
            event_id=event_id or ServiceUUID.generate_event_id(),
            session_id=session_id or ServiceUUID.generate_session_id(),
            node_name=node_name,
            operation=operation,
            additional_data=additional_data,
        )
