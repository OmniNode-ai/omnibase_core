# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""NodeComplianceOrchestrator — fans out compliance checks per contract.

Discovers all ``contract.yaml`` files under the target directory and produces
one check-request intent per contract for downstream COMPUTE nodes.

ONEX node type: ORCHESTRATOR
Handler output: events[] (orchestrators emit, never return results)

.. versionadded:: OMN-7072
"""

from __future__ import annotations

from pathlib import Path
from uuid import uuid4

from omnibase_core.models.nodes.compliance_orchestrator.model_check_request_intent import (
    ModelCheckRequestIntent,
)
from omnibase_core.models.nodes.compliance_orchestrator.model_compliance_orchestrator_result import (
    ModelComplianceOrchestratorResult,
)
from omnibase_core.models.nodes.compliance_orchestrator.model_scan_request import (
    ModelScanRequest,
)

__all__ = ["NodeComplianceOrchestrator"]


class NodeComplianceOrchestrator:
    """Discover contracts and fan out one check request per contract.

    This handler is intentionally simple: it walks a directory tree for
    ``contract.yaml`` files and produces one intent per file. The actual
    compliance checking is done by downstream COMPUTE nodes.
    """

    def discover_contracts(self, target_dir: str) -> list[Path]:
        """Walk ``target_dir`` and return paths to all contract.yaml files."""
        root = Path(target_dir)
        if not root.is_dir():
            return []
        return sorted(root.rglob("contract.yaml"))

    def handle(self, request: ModelScanRequest) -> ModelComplianceOrchestratorResult:
        """Fan out one check-requested intent per discovered contract.

        Args:
            request: Scan request with target directory and run ID.

        Returns:
            Orchestrator result with list of check-request intents.
        """
        run_id = request.run_id or str(uuid4())
        contracts = self.discover_contracts(request.target_dir)

        intents: list[ModelCheckRequestIntent] = []
        for contract_path in contracts:
            node_id = contract_path.parent.name
            intents.append(
                ModelCheckRequestIntent(
                    contract_path=str(contract_path),
                    node_id=node_id,
                    run_id=run_id,
                )
            )

        return ModelComplianceOrchestratorResult(
            intents=intents,
            contracts_discovered=len(contracts),
            run_id=run_id,
        )
