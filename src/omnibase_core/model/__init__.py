# === OmniNode:Metadata ===
# author: OmniNode Team
# copyright: OmniNode.ai
# created_at: '2025-05-28T13:24:07.849824'
# description: Stamped by ToolPython
# entrypoint: python://__init__
# hash: 4d598ad148ef850421a43c4acc573cf86e767379b0cc71918fe69a73b729ccd6
# last_modified_at: '2025-05-29T14:13:58.726636+00:00'
# lifecycle: active
# meta_type: tool
# metadata_version: 0.1.0
# name: __init__.py
# namespace: python://omnibase.model.__init__
# protocol_version: 0.1.0
# runtime_language_hint: python>=3.11
# schema_version: 0.1.0
# state_contract: state_contract://default
# tools: {}
# uuid: 5ef4541a-532c-4bc5-b738-d5264b55c571
# version: 1.0.0
# === /OmniNode:Metadata ===

"""
ONEX Model Package - Domain-based Architecture

Models are organized into functional domains:
- core/: Foundational models, shared types, contracts (95 models)
- service/: Service configurations, event bus, orchestration (23 models)
- registry/: Registry-specific models and operations (10 models)
- configuration/: Connection configs, handlers, metadata (37 models)
- validation/: Validation results, schema validation, testing (8+ models)
- workflow/: Workflow orchestration, execution, node management (replaces scenarios)
- security/: Authentication, authorization, secrets (12 models)
- health/: Health monitoring and tool health (8 models)
- endpoints/: Service endpoints and API configurations (1 model)
- detection/: Service detection and auto-discovery (1 model)
- dag/: Workflow execution, orchestration, node status (4 models)
- discovery/: Tool discovery, configuration, results (3+ models)
- execution/: Execution context, metadata, results (3 models)

Total: 210+ models across 13 domains

This __init__.py maintains backward compatibility by re-exporting
all models at the package level.
"""

# Cross-domain interface
from . import __exposed__
from .configuration import *
# Import all domain models to maintain backward compatibility
from .core import *
# Import specific backward compatibility models
from .core.model_result_cli import *
from .detection import *
from .discovery import *
from .endpoints import *
from .execution import *
from .health import *
from .registry import *
# Scenario models removed - migrated to workflows
from .security import *
from .service import *
from .validation import *
# New domains for Workflow orchestration and execution
from .workflow import *

# Re-export domains for direct access
__all__ = [
    # Domains
    "core",
    "service",
    "registry",
    "configuration",
    "validation",
    # "scenario",  # Removed - migrated to workflows
    "security",
    "health",
    "endpoints",
    "detection",
    "__exposed__",
    # New domains for Workflow orchestration
    "dag",
    "discovery",
    "execution",
    # Note: Individual model exports are handled by domain __init__.py files
    # through star imports above, maintaining full backward compatibility
]

from omnibase_core.model.configuration.model_resource_limits import \
    ModelResourceLimits
from omnibase_core.model.core import (ModelHealthCheckResult,
                                      ModelIntrospectionData,
                                      ModelResourceAllocation)
from omnibase_core.model.core.model_audit_entry import ModelAuditEntry
from omnibase_core.model.core.model_environment import ModelEnvironment
from omnibase_core.model.core.model_generic_metadata import \
    ModelGenericMetadata
from omnibase_core.model.core.model_generic_properties import \
    ModelGenericProperties
from omnibase_core.model.core.model_monitoring_metrics import \
    ModelMonitoringMetrics
from omnibase_core.model.registry.model_registry_config import \
    ModelRegistryConfig
from omnibase_core.model.registry.model_registry_health_report import \
    ModelRegistryHealthReport
from omnibase_core.model.registry.model_registry_validation_result import \
    ModelRegistryValidationResult
# Phase 2 imports for generic dict replacement
from omnibase_core.model.security import (ModelSecurityContext,
                                          ModelSecurityPolicy)
from omnibase_core.model.security.model_security_level import \
    ModelSecurityLevel

# Rebuild models with forward references after all imports
# Scenario models removed - migrated to workflows


# Rebuild models now that their forward references are available
# ScenarioConfigModel.model_rebuild()  # Removed - migrated to workflows
ModelRegistryValidationResult.model_rebuild()
ModelRegistryHealthReport.model_rebuild()
ModelEnvironment.model_rebuild()

# Rebuild models with forward references after TYPE_CHECKING imports
from omnibase_core.model.core.model_fallback_strategy import \
    ModelFallbackStrategy

ModelFallbackStrategy.model_rebuild()
