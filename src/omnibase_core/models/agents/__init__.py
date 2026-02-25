# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Agent definition models for YAML schema validation.

This package provides Pydantic models for validating agent YAML configuration
files used in the ONEX framework. The models support the 53 agent configurations
in omniclaude and enforce structural consistency across agent definitions.

Example:
    >>> import yaml
    >>> from omnibase_core.models.agents import ModelAgentDefinition
    >>> with open("agent.yaml") as f:
    ...     data = yaml.safe_load(f)
    >>> agent = ModelAgentDefinition.model_validate(data)
"""

from omnibase_core.models.agents.converter_agent_definition import (
    TypedDictAgentRoutingConfig,
    to_routing_config,
)
from omnibase_core.models.agents.model_activation_patterns import (
    ModelActivationPatterns,
)
from omnibase_core.models.agents.model_agent_capabilities import ModelAgentCapabilities
from omnibase_core.models.agents.model_agent_definition import ModelAgentDefinition
from omnibase_core.models.agents.model_agent_identity import ModelAgentIdentity
from omnibase_core.models.agents.model_agent_philosophy import ModelAgentPhilosophy
from omnibase_core.models.agents.model_domain_queries import ModelDomainQueries
from omnibase_core.models.agents.model_framework_integration import (
    ModelFrameworkIntegration,
)
from omnibase_core.models.agents.model_integration_points import ModelIntegrationPoints
from omnibase_core.models.agents.model_intelligence_integration import (
    ModelIntelligenceIntegration,
)
from omnibase_core.models.agents.model_onex_integration import ModelOnexIntegration
from omnibase_core.models.agents.model_quality_gates import ModelQualityGates
from omnibase_core.models.agents.model_rag_queries import ModelRagQueries
from omnibase_core.models.agents.model_success_metrics import ModelSuccessMetrics
from omnibase_core.models.agents.model_transformation_context import (
    ModelTransformationContext,
)
from omnibase_core.models.agents.model_workflow_phase import ModelWorkflowPhase
from omnibase_core.models.agents.model_workflow_templates import ModelWorkflowTemplates

__all__ = [
    "ModelActivationPatterns",
    "ModelAgentCapabilities",
    "ModelAgentDefinition",
    "ModelAgentIdentity",
    "ModelAgentPhilosophy",
    "ModelDomainQueries",
    "ModelFrameworkIntegration",
    "ModelIntegrationPoints",
    "ModelIntelligenceIntegration",
    "ModelOnexIntegration",
    "ModelQualityGates",
    "ModelRagQueries",
    "ModelSuccessMetrics",
    "ModelTransformationContext",
    "ModelWorkflowPhase",
    "ModelWorkflowTemplates",
    "TypedDictAgentRoutingConfig",
    "to_routing_config",
]
