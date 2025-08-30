"""
Document Freshness Worker Configuration Model

Configuration for document freshness worker operations with PostgreSQL integration.
"""

import os
from typing import List

from pydantic import BaseModel, ConfigDict, Field


class ModelDocumentFreshnessWorkerConfig(BaseModel):
    """Configuration for the document freshness worker."""

    model_config = ConfigDict(
        str_strip_whitespace=True, validate_assignment=True, extra="forbid"
    )

    # PostgreSQL connection configuration (from environment variables)
    db_host: str = Field(
        default_factory=lambda: os.getenv("POSTGRES_HOST", "localhost"),
        description="PostgreSQL database host",
    )
    db_port: int = Field(
        default_factory=lambda: int(os.getenv("POSTGRES_PORT", "5432")),
        description="PostgreSQL database port",
    )
    db_name: str = Field(
        default_factory=lambda: os.getenv("POSTGRES_DB", "onex_dev"),
        description="PostgreSQL database name",
    )
    db_user: str = Field(
        default_factory=lambda: os.getenv("POSTGRES_USER", "postgres"),
        description="PostgreSQL database user",
    )
    db_password: str = Field(
        default_factory=lambda: os.getenv("POSTGRES_PASSWORD", ""),
        description="PostgreSQL database password",
    )
    ai_analysis_enabled: bool = Field(
        default=False, description="Whether to enable AI-powered semantic analysis"
    )
    recursive: bool = Field(
        default=True, description="Whether to recursively monitor subdirectories"
    )
    include_patterns: List[str] = Field(
        default_factory=list, description="File patterns to include in monitoring"
    )
    exclude_patterns: List[str] = Field(
        default_factory=lambda: ["*.tmp", "*.log", ".git/*", "__pycache__/*"],
        description="File patterns to exclude from monitoring",
    )
    time_window: str = Field(
        default="7d",
        description="Time window for freshness analysis (e.g., '7d', '30d')",
    )
