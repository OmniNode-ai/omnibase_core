"""
Orchestrator model definitions.

This module now imports from separated model files for better organization
and compliance with one-model-per-file naming conventions.
"""

from .model_orchestrator_graph import ModelOrchestratorGraph
from .model_orchestrator_plan import ModelOrchestratorPlan
from .model_orchestrator_result import ModelOrchestratorResult

# Compatibility aliases
OrchestratorGraphModel = ModelOrchestratorGraph
OrchestratorPlanModel = ModelOrchestratorPlan
OrchestratorResultModel = ModelOrchestratorResult

# Re-export for current standards
__all__ = [
    "ModelOrchestratorGraph",
    "ModelOrchestratorPlan",
    "ModelOrchestratorResult",
]

# === OmniNode:Metadata ===
# author: OmniNode Team
# copyright: OmniNode.ai
# created_at: '2025-05-28T13:24:08.023909'
# description: Stamped by ToolPython
# entrypoint: python://model_orchestrator
# hash: c840532c0f1a1ed0d0b21040d31d99a2e211ec4ae1551238633c39a646bee261
# last_modified_at: '2025-05-29T14:13:58.898033+00:00'
# lifecycle: active
# meta_type: tool
# metadata_version: 0.1.0
# name: model_orchestrator.py
# namespace: python://omnibase.model.model_orchestrator
# owner: OmniNode Team
# protocol_version: 0.1.0
# runtime_language_hint: python>=3.11
# schema_version: 0.1.0
# state_contract: state_contract://default
# tools: {}
# uuid: e9e659e0-379d-4d2a-adc4-b89720af3f38
# version: 1.0.0
# === /OmniNode:Metadata ===
