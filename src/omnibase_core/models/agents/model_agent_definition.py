# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Top-level agent definition model for YAML schema validation."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.models.agents.model_activation_patterns import (
    ModelActivationPatterns,
)
from omnibase_core.models.agents.model_agent_capabilities import ModelAgentCapabilities
from omnibase_core.models.agents.model_agent_identity import ModelAgentIdentity
from omnibase_core.models.agents.model_agent_philosophy import ModelAgentPhilosophy
from omnibase_core.models.agents.model_framework_integration import (
    ModelFrameworkIntegration,
)
from omnibase_core.models.agents.model_integration_points import ModelIntegrationPoints
from omnibase_core.models.agents.model_intelligence_integration import (
    ModelIntelligenceIntegration,
)
from omnibase_core.models.agents.model_onex_integration import ModelOnexIntegration
from omnibase_core.models.agents.model_quality_gates import ModelQualityGates
from omnibase_core.models.agents.model_success_metrics import ModelSuccessMetrics
from omnibase_core.models.agents.model_transformation_context import (
    ModelTransformationContext,
)
from omnibase_core.models.agents.model_workflow_templates import ModelWorkflowTemplates


class ModelAgentDefinition(BaseModel):
    """Top-level agent definition model.

    This is the primary model for validating agent YAML configuration files.
    It captures the complete definition of an agent including identity,
    philosophy, capabilities, and integration points.

    Required fields (>90% presence across agent configs):
        schema_version: Version of the agent schema being used
        agent_type: Type classification of the agent
        agent_identity: Core identity and metadata
        onex_integration: ONEX framework integration settings
        agent_philosophy: Guiding principles and mission
        capabilities: What the agent can do
        intelligence_integration: AI/ML integration settings

    Optional fields (<90% presence):
        definition_format: Optional format specifier
        framework_integration: Optional external framework integration
        claude_skills_references: Optional Claude skills to reference
        activation_patterns: Optional activation/routing patterns
        workflow_templates: Optional workflow phase templates
        quality_gates: Optional quality requirements
        success_metrics: Optional success measurement criteria
        integration_points: Optional agent collaboration points
        transformation_context: Optional polymorphic transformation settings

    Note: Unknown fields are silently ignored (extra="ignore") for
    forward compatibility with agent-specific custom sections.

    Example:
        >>> import yaml
        >>> with open("agent.yaml") as f:
        ...     data = yaml.safe_load(f)
        >>> agent = ModelAgentDefinition.model_validate(data)
    """

    model_config = ConfigDict(frozen=True, extra="ignore", from_attributes=True)

    # Required fields (>90% presence)
    schema_version: str = Field(..., description="Schema version")
    agent_type: str = Field(..., description="Agent type identifier")
    agent_identity: ModelAgentIdentity
    onex_integration: ModelOnexIntegration
    agent_philosophy: ModelAgentPhilosophy
    capabilities: ModelAgentCapabilities
    intelligence_integration: ModelIntelligenceIntegration

    # Optional fields (<90% presence)
    definition_format: str | None = None
    framework_integration: ModelFrameworkIntegration | None = None
    claude_skills_references: list[str] | None = None
    activation_patterns: ModelActivationPatterns | None = None
    workflow_templates: ModelWorkflowTemplates | None = None
    quality_gates: ModelQualityGates | None = None
    success_metrics: ModelSuccessMetrics | None = None
    integration_points: ModelIntegrationPoints | None = None
    transformation_context: ModelTransformationContext | None = None


__all__ = ["ModelAgentDefinition"]
