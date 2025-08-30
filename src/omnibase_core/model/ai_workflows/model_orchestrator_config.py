"""
AI Orchestrator Configuration Models

Security and resource configuration for AI workflow orchestration
with ONEX compliance standards.
"""

import os
from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field


class EnumSecurityLevel(Enum):
    """Security levels for command execution."""

    STRICT = "strict"  # Only allow predefined commands
    MODERATE = "moderate"  # Allow git and safe commands
    PERMISSIVE = "permissive"  # Allow most commands with validation


class EnumResourceLimitType(Enum):
    """Types of resource limits."""

    MEMORY_MB = "memory_mb"
    CPU_PERCENT = "cpu_percent"
    DISK_MB = "disk_mb"
    NETWORK_BPS = "network_bps"
    EXECUTION_TIME_SECONDS = "execution_time_seconds"


class ModelSecurityConfig(BaseModel):
    """Security configuration for AI orchestrator."""

    security_level: EnumSecurityLevel = Field(
        default=EnumSecurityLevel.STRICT,
        description="Overall security level for command execution",
    )

    allowed_commands: List[str] = Field(
        default_factory=lambda: ["git", "gh", "cat", "ls", "pwd"],
        description="List of allowed command prefixes",
    )

    blocked_commands: List[str] = Field(
        default_factory=lambda: ["rm", "sudo", "chmod", "chown", "dd", "mount"],
        description="List of explicitly blocked commands",
    )

    max_command_length: int = Field(
        default=1000, description="Maximum length of any command string", gt=0
    )

    enable_input_sanitization: bool = Field(
        default=True, description="Whether to sanitize all external inputs"
    )

    require_command_approval: bool = Field(
        default=False, description="Whether commands require manual approval"
    )

    enable_security_logging: bool = Field(
        default=True, description="Whether to log security-sensitive operations"
    )


class ModelResourceLimits(BaseModel):
    """Resource limits for workflow execution."""

    max_workflow_duration_seconds: int = Field(
        default=1800,  # 30 minutes
        description="Maximum duration for any workflow",
        gt=0,
    )

    max_llm_inference_timeout_seconds: int = Field(
        default=300, description="Maximum timeout for LLM inference", gt=0  # 5 minutes
    )

    max_concurrent_workflows: int = Field(
        default=5, description="Maximum concurrent workflows", gt=0
    )

    max_memory_usage_mb: int = Field(
        default=2048, description="Maximum memory usage in MB", gt=0  # 2GB
    )

    max_document_size_mb: int = Field(
        default=10, description="Maximum document size for processing", gt=0
    )

    max_prompt_length: int = Field(
        default=50000, description="Maximum prompt length in characters", gt=0
    )


class ModelOrchestratorConfig(BaseModel):
    """Complete orchestrator configuration."""

    # Event bus configuration
    event_bus_url: str = Field(
        default_factory=lambda: os.getenv("EVENT_BUS_URL", "http://localhost:8083"),
        description="Event bus connection URL",
    )

    event_bus_timeout_seconds: int = Field(
        default=30, description="Event bus connection timeout", gt=0
    )

    # LLM service configuration
    ollama_url: str = Field(
        default="http://localhost:11434", description="Ollama service URL"
    )

    default_model: str = Field(
        default="llama3.1:latest", description="Default model for inference"
    )

    # Security and resource limits
    security_config: ModelSecurityConfig = Field(
        default_factory=ModelSecurityConfig, description="Security configuration"
    )

    resource_limits: ModelResourceLimits = Field(
        default_factory=ModelResourceLimits, description="Resource limits configuration"
    )

    # Workflow behavior
    auto_cleanup_completed_workflows: bool = Field(
        default=True, description="Whether to auto-cleanup completed workflows"
    )

    workflow_cleanup_delay_seconds: int = Field(
        default=3600,  # 1 hour
        description="Delay before cleaning up completed workflows",
        gt=0,
    )

    enable_metrics_collection: bool = Field(
        default=True, description="Whether to collect performance metrics"
    )

    metrics_export_interval_seconds: int = Field(
        default=300, description="Interval for metrics export", gt=0  # 5 minutes
    )


class ModelValidationResult(BaseModel):
    """Result of input validation."""

    is_valid: bool = Field(description="Whether input is valid")
    sanitized_input: Optional[str] = Field(
        default=None, description="Sanitized version of input if valid"
    )
    error_message: Optional[str] = Field(
        default=None, description="Error message if invalid"
    )
    validation_warnings: List[str] = Field(
        default_factory=list, description="Non-fatal validation warnings"
    )
