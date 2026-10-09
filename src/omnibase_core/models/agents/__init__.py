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

from __future__ import annotations

import importlib
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from omnibase_core.models.agents.model_activation_patterns import (
        ModelActivationPatterns,
    )
    from omnibase_core.models.agents.model_agent_capabilities import (
        ModelAgentCapabilities,
    )
    from omnibase_core.models.agents.model_agent_definition import ModelAgentDefinition
    from omnibase_core.models.agents.model_agent_identity import ModelAgentIdentity
    from omnibase_core.models.agents.model_agent_philosophy import ModelAgentPhilosophy
    from omnibase_core.models.agents.model_agent_yaml_config import ModelAgentConfig
    from omnibase_core.models.agents.model_converter_agent_definition import (
        TypedDictAgentRoutingConfig,
        to_routing_config,
    )
    from omnibase_core.models.agents.model_domain_queries import ModelDomainQueries
    from omnibase_core.models.agents.model_framework_integration import (
        ModelFrameworkIntegration,
    )
    from omnibase_core.models.agents.model_integration_points import (
        ModelIntegrationPoints,
    )
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
    from omnibase_core.models.agents.model_workflow_templates import (
        ModelWorkflowTemplates,
    )

__all__ = [
    "ModelActivationPatterns",
    "ModelAgentCapabilities",
    "ModelAgentConfig",
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


# PEP 562 lazy re-exports (OMN-17427). Importing this package used to import
# every module re-exported above, and Python runs a package's __init__ before
# any of its submodules, so even one leaf import paid for the whole subtree.
# Names now load on first access; ``from <package> import Name`` and
# ``<package>.Name`` behave as before.
_LAZY_IMPORTS: dict[str, tuple[str, str | None]] = {
    "ModelActivationPatterns": (
        "omnibase_core.models.agents.model_activation_patterns",
        "ModelActivationPatterns",
    ),
    "ModelAgentCapabilities": (
        "omnibase_core.models.agents.model_agent_capabilities",
        "ModelAgentCapabilities",
    ),
    "ModelAgentDefinition": (
        "omnibase_core.models.agents.model_agent_definition",
        "ModelAgentDefinition",
    ),
    "ModelAgentIdentity": (
        "omnibase_core.models.agents.model_agent_identity",
        "ModelAgentIdentity",
    ),
    "ModelAgentPhilosophy": (
        "omnibase_core.models.agents.model_agent_philosophy",
        "ModelAgentPhilosophy",
    ),
    "ModelAgentConfig": (
        "omnibase_core.models.agents.model_agent_yaml_config",
        "ModelAgentConfig",
    ),
    "TypedDictAgentRoutingConfig": (
        "omnibase_core.models.agents.model_converter_agent_definition",
        "TypedDictAgentRoutingConfig",
    ),
    "to_routing_config": (
        "omnibase_core.models.agents.model_converter_agent_definition",
        "to_routing_config",
    ),
    "ModelDomainQueries": (
        "omnibase_core.models.agents.model_domain_queries",
        "ModelDomainQueries",
    ),
    "ModelFrameworkIntegration": (
        "omnibase_core.models.agents.model_framework_integration",
        "ModelFrameworkIntegration",
    ),
    "ModelIntegrationPoints": (
        "omnibase_core.models.agents.model_integration_points",
        "ModelIntegrationPoints",
    ),
    "ModelIntelligenceIntegration": (
        "omnibase_core.models.agents.model_intelligence_integration",
        "ModelIntelligenceIntegration",
    ),
    "ModelOnexIntegration": (
        "omnibase_core.models.agents.model_onex_integration",
        "ModelOnexIntegration",
    ),
    "ModelQualityGates": (
        "omnibase_core.models.agents.model_quality_gates",
        "ModelQualityGates",
    ),
    "ModelRagQueries": (
        "omnibase_core.models.agents.model_rag_queries",
        "ModelRagQueries",
    ),
    "ModelSuccessMetrics": (
        "omnibase_core.models.agents.model_success_metrics",
        "ModelSuccessMetrics",
    ),
    "ModelTransformationContext": (
        "omnibase_core.models.agents.model_transformation_context",
        "ModelTransformationContext",
    ),
    "ModelWorkflowPhase": (
        "omnibase_core.models.agents.model_workflow_phase",
        "ModelWorkflowPhase",
    ),
    "ModelWorkflowTemplates": (
        "omnibase_core.models.agents.model_workflow_templates",
        "ModelWorkflowTemplates",
    ),
}


def __getattr__(name: str) -> object:
    target = _LAZY_IMPORTS.get(name)
    if target is None:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    module = importlib.import_module(target[0])
    value = module if target[1] is None else getattr(module, target[1])
    globals()[name] = value
    return value


def __dir__() -> list[str]:
    return sorted({*globals(), *_LAZY_IMPORTS})
