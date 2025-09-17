"""
Configuration constants for WorkflowOrchestratorAgent.

This module provides centralized configuration constants to avoid hard-coded
values throughout the agent implementation.
"""

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class WorkflowOrchestratorConfig:
    """Configuration constants for WorkflowOrchestratorAgent."""

    # Health check thresholds
    MAX_ACTIVE_WORKFLOWS_WARNING: int = int(
        os.getenv("MAX_ACTIVE_WORKFLOWS_WARNING", "100")
    )
    MAX_TOTAL_WORKFLOWS_WARNING: int = int(
        os.getenv("MAX_TOTAL_WORKFLOWS_WARNING", "1000")
    )
    HEALTH_SCORE_WARNING_THRESHOLD: float = float(
        os.getenv("HEALTH_SCORE_WARNING_THRESHOLD", "0.7")
    )
    HEALTH_SCORE_MEMORY_THRESHOLD: float = float(
        os.getenv("HEALTH_SCORE_MEMORY_THRESHOLD", "0.8")
    )

    # Memory management
    EXECUTION_STATE_TTL_SECONDS: int = int(
        os.getenv("EXECUTION_STATE_TTL_SECONDS", "3600")
    )  # 1 hour
    CLEANUP_INTERVAL_SECONDS: int = int(
        os.getenv("CLEANUP_INTERVAL_SECONDS", "300")
    )  # 5 minutes
    MAX_EXECUTION_STATES: int = int(os.getenv("MAX_EXECUTION_STATES", "5000"))

    # Retry and timeout configuration
    DEFAULT_RETRY_COUNT: int = int(os.getenv("DEFAULT_RETRY_COUNT", "3"))
    DEFAULT_TIMEOUT_SECONDS: int = int(os.getenv("DEFAULT_TIMEOUT_SECONDS", "300"))
    RETRY_BACKOFF_MULTIPLIER: float = float(
        os.getenv("RETRY_BACKOFF_MULTIPLIER", "2.0")
    )
    MAX_RETRY_DELAY_SECONDS: int = int(os.getenv("MAX_RETRY_DELAY_SECONDS", "60"))

    # Performance optimization
    OPERATION_HANDLER_CACHE_ENABLED: bool = (
        os.getenv("OPERATION_HANDLER_CACHE_ENABLED", "true").lower() == "true"
    )

    # Thread safety
    REGISTRY_ACCESS_TIMEOUT_SECONDS: float = float(
        os.getenv("REGISTRY_ACCESS_TIMEOUT_SECONDS", "5.0")
    )


# Global configuration instance
CONFIG = WorkflowOrchestratorConfig()
