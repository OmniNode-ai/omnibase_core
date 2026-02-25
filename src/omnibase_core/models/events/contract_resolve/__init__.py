# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Event models for the contract.resolve compute node lifecycle.

Event types:
    - ``onex.contract.resolve.requested`` — resolve operation started
    - ``onex.contract.resolve.completed`` — resolve operation completed

.. versionadded:: OMN-2754
"""

from omnibase_core.models.events.contract_resolve.model_contract_resolve_completed_event import (
    CONTRACT_RESOLVE_COMPLETED_EVENT,
    ModelContractResolveCompletedEvent,
)
from omnibase_core.models.events.contract_resolve.model_contract_resolve_requested_event import (
    CONTRACT_RESOLVE_REQUESTED_EVENT,
    ModelContractResolveRequestedEvent,
)

__all__ = [
    "CONTRACT_RESOLVE_REQUESTED_EVENT",
    "CONTRACT_RESOLVE_COMPLETED_EVENT",
    "ModelContractResolveRequestedEvent",
    "ModelContractResolveCompletedEvent",
]
