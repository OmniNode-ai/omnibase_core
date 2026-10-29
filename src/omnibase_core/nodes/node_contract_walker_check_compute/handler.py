# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""Typed contract walking, delegating to the validation-layer walker."""

from __future__ import annotations

from omnibase_core.models.nodes.contract_walker_check.model_contract_walker_check_input import (
    ModelContractWalkerCheckInput,
)
from omnibase_core.models.validation.model_contract_walk_report import (
    ModelContractWalkReport,
)
from omnibase_core.validation.validator_contract_walker import (
    DEFAULT_MAX_PRODUCT_STATES,
    walk_contracts,
)


class NodeContractWalkerCheckCompute:
    """Walk every machine-declaring contract under the supplied roots."""

    def handle(self, request: ModelContractWalkerCheckInput) -> ModelContractWalkReport:
        """Return the walk report."""
        cap = request.max_product_states
        return walk_contracts(
            request.roots,
            max_product_states=DEFAULT_MAX_PRODUCT_STATES if cap is None else cap,
        )
