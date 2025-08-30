#!/usr/bin/env python3
"""
ONEX Mock Registry Models

This module provides strongly typed Pydantic models for mock registry service
to replace Any usage with proper type safety.
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field

from omnibase_core.model.core.model_semver import ModelSemVer


class ModelMockRegistryConfig(BaseModel):
    """Configuration model for mock registry behavior"""

    deterministic_responses: dict[str, dict[str, dict]] = Field(
        default_factory=dict,
        description="Deterministic responses for different methods",
    )
    tool_registry: dict[str, dict] = Field(
        default_factory=dict, description="Mock tool registry data"
    )
    failure_injection: dict[str, bool] = Field(
        default_factory=dict, description="Failure injection configuration"
    )


class ModelMockToolInfo(BaseModel):
    """Model for mock tool information"""

    tool_identifier: str = Field(description="Tool identifier")
    tool_name: str = Field(description="Tool name")
    tool_version: ModelSemVer = Field(description="Tool version")
    tool_type: str = Field(description="Type of tool")
    implementation_class: str = Field(description="Implementation class path")
    description: str = Field(description="Tool description")
    author: str = Field(description="Tool author")
    created_at: datetime = Field(description="When tool was registered")
    is_mock: bool = Field(default=True, description="Whether this is a mock tool")


class ModelRegistryResponse(BaseModel):
    """Model for registry operation response"""

    status: str = Field(description="Operation status")
    tool_identifier: str = Field(description="Tool identifier")
    operation: str = Field(description="Operation performed")
    timestamp: str = Field(description="Response timestamp")
    success: bool = Field(description="Whether operation succeeded")
    message: Optional[str] = Field(default=None, description="Response message")


class ModelPureToolResponse(BaseModel):
    """Model for pure tool retrieval response"""

    tool_identifier: str = Field(description="Tool identifier")
    tool_instance: Optional[str] = Field(
        default=None, description="Tool instance class name (mock)"
    )
    retrieval_successful: bool = Field(description="Whether retrieval succeeded")
    timestamp: str = Field(description="Response timestamp")
    mock_behavior: str = Field(description="Mock behavior applied")


class ModelMockRegistryState(BaseModel):
    """Model for mock registry state"""

    total_tools_registered: int = Field(description="Total tools in mock registry")
    total_retrievals: int = Field(description="Total tool retrievals performed")
    failure_injection_enabled: bool = Field(
        description="Whether failure injection is enabled"
    )
    failure_injection_type: Optional[str] = Field(
        default=None, description="Type of failure injection active"
    )
    last_operation: str = Field(description="Last operation performed")
    last_operation_timestamp: str = Field(description="When last operation occurred")
