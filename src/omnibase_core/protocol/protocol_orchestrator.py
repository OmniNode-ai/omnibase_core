# === OmniNode:Metadata ===
# author: OmniNode Team
# copyright: OmniNode.ai
# created_at: '2025-05-28T12:36:27.245096'
# description: Stamped by ToolPython
# entrypoint: python://protocol_orchestrator
# hash: 97f3deb8b8a9392539a52dfda4cdc7af0929d195897f0a11b292637d0614a372
# last_modified_at: '2025-05-29T14:14:00.303902+00:00'
# lifecycle: active
# meta_type: tool
# metadata_version: 0.1.0
# name: protocol_orchestrator.py
# namespace: python://omnibase.protocol.protocol_orchestrator
# owner: OmniNode Team
# protocol_version: 0.1.0
# runtime_language_hint: python>=3.11
# schema_version: 0.1.0
# state_contract: state_contract://default
# tools: null
# uuid: 4ea8f61f-93a5-4e91-91ad-75b22a6b4060
# version: 1.0.0
# === /OmniNode:Metadata ===


from typing import List, Protocol

from omnibase_core.model.service.model_orchestrator import (
    GraphModel, OrchestratorResultModel, PlanModel)


class ProtocolOrchestrator(Protocol):
    """
    Protocol for ONEX orchestrator components (workflow/graph execution).

    Example:
        class MyOrchestrator:
            def plan(self, graph: GraphModel) -> List[PlanModel]:
                ...
            def execute(self, plan: List[PlanModel]) -> OrchestratorResultModel:
                ...
    """

    def plan(self, graph: GraphModel) -> List[PlanModel]: ...

    def execute(self, plan: List[PlanModel]) -> OrchestratorResultModel: ...
