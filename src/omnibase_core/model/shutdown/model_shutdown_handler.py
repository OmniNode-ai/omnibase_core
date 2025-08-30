"""
ONEX-compliant model for graceful shutdown handlers.

Defines shutdown handler configuration and execution tracking
for coordinated application lifecycle management.
"""

from datetime import datetime
from enum import Enum
from typing import Optional
from uuid import uuid4

from pydantic import BaseModel, Field


class EnumShutdownPhase(str, Enum):
    """Shutdown phase enumeration."""

    RUNNING = "running"
    STOP_ACCEPTING = "stop_accepting"
    FINISH_REQUESTS = "finish_requests"
    CLEANUP_RESOURCES = "cleanup_resources"
    FINAL_CLEANUP = "final_cleanup"
    FORCE_SHUTDOWN = "force_shutdown"


class EnumShutdownPriority(str, Enum):
    """Shutdown handler priority enumeration."""

    CRITICAL = "critical"  # Must complete first (load balancer removal, etc.)
    HIGH = "high"  # Important cleanup (database connections, etc.)
    NORMAL = "normal"  # Standard cleanup (caches, temporary files, etc.)
    LOW = "low"  # Optional cleanup (metrics, logging, etc.)


class ModelShutdownHandler(BaseModel):
    """
    Shutdown handler configuration model.

    Defines a handler function that will be executed during
    graceful shutdown with proper priority and timeout management.
    """

    handler_id: str = Field(
        default_factory=lambda: str(uuid4()), description="Unique handler identifier"
    )
    name: str = Field(..., description="Human-readable handler name")
    handler_function: str = Field(..., description="Name of the handler function")

    # Execution configuration
    priority: EnumShutdownPriority = Field(
        EnumShutdownPriority.NORMAL, description="Handler execution priority"
    )
    timeout: float = Field(15.0, description="Handler execution timeout in seconds")
    required: bool = Field(
        True, description="Whether handler must complete successfully"
    )

    # Execution tracking
    registered_at: datetime = Field(
        default_factory=datetime.now, description="When handler was registered"
    )
    started_at: Optional[datetime] = Field(
        None, description="When handler execution started"
    )
    completed_at: Optional[datetime] = Field(
        None, description="When handler execution completed"
    )

    # Results
    success: bool = Field(False, description="Whether handler completed successfully")
    error_message: Optional[str] = Field(
        None, description="Error message if handler failed"
    )

    # Metadata
    description: Optional[str] = Field(None, description="Handler description")
    tags: dict = Field(default_factory=dict, description="Handler metadata tags")

    class Config:
        """Pydantic configuration."""

        json_schema_extra = {
            "example": {
                "handler_id": "550e8400-e29b-41d4-a716-446655440000",
                "name": "database_cleanup",
                "handler_function": "cleanup_database_connections",
                "priority": "high",
                "timeout": 30.0,
                "required": True,
                "registered_at": "2025-07-30T12:00:00Z",
                "started_at": "2025-07-30T12:05:00Z",
                "completed_at": "2025-07-30T12:05:15Z",
                "success": True,
                "description": "Clean up database connection pools",
                "tags": {"component": "database", "criticality": "high"},
            }
        }


class ModelShutdownConfiguration(BaseModel):
    """
    Shutdown configuration model.

    Global configuration for graceful shutdown behavior
    including timeouts and policies.
    """

    # Timeout configuration
    total_shutdown_timeout: float = Field(
        60.0, description="Total shutdown timeout in seconds"
    )
    phase_timeout: float = Field(20.0, description="Per-phase timeout in seconds")
    handler_default_timeout: float = Field(
        15.0, description="Default handler timeout in seconds"
    )

    # Signal handling
    handle_sigterm: bool = Field(True, description="Handle SIGTERM signal")
    handle_sigint: bool = Field(True, description="Handle SIGINT signal")
    handle_sigusr1: bool = Field(
        True, description="Handle SIGUSR1 signal for graceful restart"
    )

    # Shutdown behavior
    force_shutdown_after_timeout: bool = Field(
        True, description="Force shutdown after timeout"
    )
    wait_for_handlers: bool = Field(
        True, description="Wait for all handlers to complete"
    )
    log_handler_progress: bool = Field(
        True, description="Log individual handler progress"
    )

    # Health check integration
    update_health_check: bool = Field(
        True, description="Update health check during shutdown"
    )
    drain_requests_timeout: float = Field(
        30.0, description="Time to wait for request draining"
    )

    class Config:
        """Pydantic configuration."""

        json_schema_extra = {
            "example": {
                "total_shutdown_timeout": 60.0,
                "phase_timeout": 20.0,
                "handler_default_timeout": 15.0,
                "handle_sigterm": True,
                "handle_sigint": True,
                "handle_sigusr1": True,
                "force_shutdown_after_timeout": True,
                "wait_for_handlers": True,
                "log_handler_progress": True,
                "update_health_check": True,
                "drain_requests_timeout": 30.0,
            }
        }


class ModelShutdownStatus(BaseModel):
    """
    Shutdown status model.

    Current status of the shutdown process including
    phase information and handler execution status.
    """

    # Current state
    shutdown_initiated: bool = Field(
        False, description="Whether shutdown has been initiated"
    )
    shutdown_completed: bool = Field(
        False, description="Whether shutdown has completed"
    )
    current_phase: EnumShutdownPhase = Field(
        EnumShutdownPhase.RUNNING, description="Current shutdown phase"
    )

    # Timing
    shutdown_started_at: Optional[datetime] = Field(
        None, description="When shutdown started"
    )
    shutdown_completed_at: Optional[datetime] = Field(
        None, description="When shutdown completed"
    )
    elapsed_time: float = Field(0.0, description="Elapsed shutdown time in seconds")

    # Handler statistics
    total_handlers: int = Field(0, description="Total number of registered handlers")
    completed_handlers: int = Field(0, description="Number of completed handlers")
    successful_handlers: int = Field(0, description="Number of successful handlers")
    failed_handlers: int = Field(0, description="Number of failed handlers")

    # Signal information
    triggering_signal: Optional[str] = Field(
        None, description="Signal that triggered shutdown"
    )
    shutdown_reason: str = Field("Unknown", description="Reason for shutdown")

    # Health status
    accepting_requests: bool = Field(
        True, description="Whether system is accepting new requests"
    )
    ready_for_termination: bool = Field(
        False, description="Whether system is ready to terminate"
    )

    class Config:
        """Pydantic configuration."""

        json_schema_extra = {
            "example": {
                "shutdown_initiated": True,
                "shutdown_completed": False,
                "current_phase": "cleanup_resources",
                "shutdown_started_at": "2025-07-30T12:05:00Z",
                "elapsed_time": 15.5,
                "total_handlers": 8,
                "completed_handlers": 6,
                "successful_handlers": 6,
                "failed_handlers": 0,
                "triggering_signal": "SIGTERM",
                "shutdown_reason": "Deployment update",
                "accepting_requests": False,
                "ready_for_termination": False,
            }
        }
