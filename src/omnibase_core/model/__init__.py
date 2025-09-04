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

# Cross-domain interface - import submodules only, no star imports
from . import __exposed__
from . import configuration
from . import core
from . import detection
from . import discovery
from . import endpoints
from . import execution
from . import health
from . import registry
from . import security
from . import service
from . import validation
from . import workflow

# Only import specific models that are actually needed at package level
# Remove the massive star imports that cause circular dependencies

# Re-export domains for direct access
__all__ = [
    "__exposed__",
    "configuration",
    # Domains
    "core",
    # New domains for Workflow orchestration
    "dag",
    "detection",
    "discovery",
    "endpoints",
    "execution",
    "health",
    "registry",
    # "scenario",  # Removed - migrated to workflows
    "security",
    "service",
    "validation",
    # Note: Individual model exports are handled by domain __init__.py files
    # through star imports above, maintaining full backward compatibility
]

# Remove specific imports to avoid circular dependencies
# These should be imported directly when needed

# Phase 2 imports for generic dict replacement

# Remove problematic model rebuilds that depend on star imports
# Models should handle their own forward references or be imported individually
# TODO: Move model rebuilds to their respective domain modules if needed
