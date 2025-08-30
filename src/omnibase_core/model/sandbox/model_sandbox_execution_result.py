#!/usr/bin/env python3
"""
ONEX Sandbox Execution Result Model.

Defines the structure for sandbox execution results with comprehensive
logging, monitoring, and security validation information.
"""

from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel, Field


class EnumSandboxExecutionStatus(str, Enum):
    """Sandbox execution status indicators."""

    PENDING = "pending"  # Execution queued
    RUNNING = "running"  # Currently executing
    COMPLETED = "completed"  # Finished successfully
    FAILED = "failed"  # Execution failed
    TIMEOUT = "timeout"  # Execution timed out
    KILLED = "killed"  # Execution terminated
    SECURITY_VIOLATION = "security_violation"  # Security policy violated


class EnumSandboxSecurityEvent(str, Enum):
    """Types of security events that can occur."""

    PRIVILEGE_ESCALATION = "privilege_escalation"
    SYSCALL_VIOLATION = "syscall_violation"
    NETWORK_VIOLATION = "network_violation"
    FILESYSTEM_VIOLATION = "filesystem_violation"
    RESOURCE_EXHAUSTION = "resource_exhaustion"
    CONTAINER_ESCAPE_ATTEMPT = "container_escape_attempt"
    MALICIOUS_CODE_DETECTED = "malicious_code_detected"


class ModelSandboxResourceUsage(BaseModel):
    """Resource usage metrics for sandbox execution."""

    peak_cpu_usage: float = Field(
        description="Peak CPU usage as percentage (0.0-100.0)"
    )

    peak_memory_usage_mb: int = Field(description="Peak memory usage in MB")

    disk_io_read_mb: float = Field(description="Total disk read I/O in MB")

    disk_io_write_mb: float = Field(description="Total disk write I/O in MB")

    network_bytes_sent: int = Field(
        default=0, description="Total bytes sent over network"
    )

    network_bytes_received: int = Field(
        default=0, description="Total bytes received over network"
    )

    execution_time_seconds: float = Field(
        description="Actual execution time in seconds"
    )

    file_descriptors_used: int = Field(description="Number of file descriptors used")

    processes_spawned: int = Field(description="Number of processes spawned")

    syscalls_made: int = Field(
        default=0, description="Total number of system calls made"
    )


class ModelSandboxSecurityEvent(BaseModel):
    """Security event detected during sandbox execution."""

    event_type: EnumSandboxSecurityEvent = Field(description="Type of security event")

    severity: str = Field(description="Event severity (LOW, MEDIUM, HIGH, CRITICAL)")

    timestamp: datetime = Field(description="When the event occurred")

    description: str = Field(description="Human-readable description of the event")

    details: Dict[str, str] = Field(
        default_factory=dict, description="Additional event details and context"
    )

    blocked: bool = Field(description="Whether the action was blocked")

    process_id: Optional[int] = Field(
        default=None, description="Process ID that triggered the event"
    )

    command: Optional[str] = Field(
        default=None, description="Command that triggered the event"
    )


class ModelSandboxExecutionLog(BaseModel):
    """Execution log entry from sandbox."""

    timestamp: datetime = Field(description="Log entry timestamp")

    level: str = Field(description="Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)")

    source: str = Field(description="Log source (stdout, stderr, system, security)")

    message: str = Field(description="Log message content")

    metadata: Dict[str, str] = Field(
        default_factory=dict, description="Additional log metadata"
    )


class ModelSandboxExecutionResult(BaseModel):
    """Complete sandbox execution result with monitoring data."""

    execution_id: UUID = Field(description="Unique identifier for this execution")

    sandbox_id: UUID = Field(description="ID of the sandbox that ran the execution")

    agent_id: UUID = Field(description="ID of the agent that requested execution")

    status: EnumSandboxExecutionStatus = Field(description="Final execution status")

    started_at: datetime = Field(description="Execution start timestamp")

    completed_at: Optional[datetime] = Field(
        default=None, description="Execution completion timestamp"
    )

    exit_code: Optional[int] = Field(
        default=None, description="Process exit code (0 = success)"
    )

    stdout: str = Field(default="", description="Standard output from execution")

    stderr: str = Field(default="", description="Standard error from execution")

    result_data: Optional[str] = Field(
        default=None, description="Structured result data from execution"
    )

    error_message: Optional[str] = Field(
        default=None, description="Error message if execution failed"
    )

    resource_usage: Optional[ModelSandboxResourceUsage] = Field(
        default=None, description="Resource usage metrics"
    )

    security_events: List[ModelSandboxSecurityEvent] = Field(
        default_factory=list, description="Security events detected during execution"
    )

    execution_logs: List[ModelSandboxExecutionLog] = Field(
        default_factory=list, description="Execution logs and output"
    )

    files_created: List[str] = Field(
        default_factory=list, description="List of files created during execution"
    )

    files_modified: List[str] = Field(
        default_factory=list, description="List of files modified during execution"
    )

    network_connections: List[str] = Field(
        default_factory=list, description="Network connections attempted"
    )

    metadata: Dict[str, str] = Field(
        default_factory=dict, description="Additional execution metadata"
    )

    def get_execution_duration(self) -> Optional[float]:
        """Calculate execution duration in seconds."""
        if self.completed_at:
            return (self.completed_at - self.started_at).total_seconds()
        return None

    def was_successful(self) -> bool:
        """Check if execution was successful."""
        return (
            self.status == EnumSandboxExecutionStatus.COMPLETED and self.exit_code == 0
        )

    def has_security_violations(self) -> bool:
        """Check if any security violations occurred."""
        return (
            self.status == EnumSandboxExecutionStatus.SECURITY_VIOLATION
            or len(self.security_events) > 0
        )

    def has_critical_security_events(self) -> bool:
        """Check if any critical security events occurred."""
        return any(event.severity == "CRITICAL" for event in self.security_events)

    def get_output_summary(self, max_length: int = 1000) -> str:
        """Get a truncated summary of stdout/stderr."""
        combined = f"STDOUT:\n{self.stdout}\n\nSTDERR:\n{self.stderr}"
        if len(combined) > max_length:
            return combined[: max_length - 3] + "..."
        return combined

    def get_security_summary(self) -> Dict[str, int]:
        """Get summary of security events by severity."""
        summary = {"CRITICAL": 0, "HIGH": 0, "MEDIUM": 0, "LOW": 0}
        for event in self.security_events:
            if event.severity in summary:
                summary[event.severity] += 1
        return summary

    def add_security_event(
        self,
        event_type: EnumSandboxSecurityEvent,
        severity: str,
        description: str,
        blocked: bool = True,
        **details,
    ) -> None:
        """Add a security event to the execution result."""
        event = ModelSandboxSecurityEvent(
            event_type=event_type,
            severity=severity,
            timestamp=datetime.utcnow(),
            description=description,
            blocked=blocked,
            details=details,
        )
        self.security_events.append(event)

        # Update status if critical security event
        if severity == "CRITICAL" and blocked:
            self.status = EnumSandboxExecutionStatus.SECURITY_VIOLATION

    def add_log_entry(self, level: str, source: str, message: str, **metadata) -> None:
        """Add a log entry to the execution result."""
        log_entry = ModelSandboxExecutionLog(
            timestamp=datetime.utcnow(),
            level=level,
            source=source,
            message=message,
            metadata=metadata,
        )
        self.execution_logs.append(log_entry)

    class Config:
        """Pydantic configuration."""

        use_enum_values = True
        json_encoders = {datetime: lambda v: v.isoformat(), UUID: lambda v: str(v)}
