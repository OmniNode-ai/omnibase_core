"""
Contract validation event models.

This module provides event models for contract validation and merge lifecycle
events in the ONEX framework. These events enable tracking and auditing of
contract validation operations.

Event Lifecycle:
    Validation: started -> passed | failed
    Merge: started -> completed

Event Types:
    - ``onex.contract.validation.started``: Validation begins
    - ``onex.contract.validation.passed``: Validation succeeds
    - ``onex.contract.validation.failed``: Validation fails
    - ``onex.contract.merge.started``: Merge operation begins
    - ``onex.contract.merge.completed``: Merge operation completes

Note:
    ModelContractValidationContext is used for contract validation operations.
    For field-level validation context (field_name, expected, actual), use
    :class:`omnibase_core.models.context.ModelValidationContext` instead.

Import Example:
    .. code-block:: python

        from omnibase_core.models.events.contract_validation import (
            # Base and reference models
            ModelContractRef,
            ModelContractValidationContext,
            ModelContractValidationEventBase,
            # Validation events
            ModelContractValidationStartedEvent,
            ModelContractValidationPassedEvent,
            ModelContractValidationFailedEvent,
            # Merge events
            ModelContractMergeStartedEvent,
            ModelContractMergeCompletedEvent,
            # Event type constants
            CONTRACT_VALIDATION_STARTED_EVENT,
            CONTRACT_VALIDATION_PASSED_EVENT,
            CONTRACT_VALIDATION_FAILED_EVENT,
            CONTRACT_MERGE_STARTED_EVENT,
            CONTRACT_MERGE_COMPLETED_EVENT,
        )

Usage Example:
    .. code-block:: python

        from uuid import uuid4
        from omnibase_core.models.events.contract_validation import (
            ModelContractValidationStartedEvent,
            ModelContractValidationPassedEvent,
            ModelContractValidationContext,
        )

        # Start validation
        run_id = uuid4()
        started_event = ModelContractValidationStartedEvent.create(
            contract_name="my-contract",
            run_id=run_id,
            context=ModelContractValidationContext(),
        )

        # ... perform validation ...

        # Emit passed event
        passed_event = ModelContractValidationPassedEvent.create(
            contract_name="my-contract",
            run_id=run_id,  # Same run_id for lifecycle correlation
            duration_ms=250,
            checks_run=15,
        )

See Also:
    - :mod:`omnibase_core.models.events`: Other event models

.. versionadded:: 0.4.0
    Initial implementation as part of OMN-1146 contract validation events.
"""

from omnibase_core.models.events.contract_validation.model_contract_merge_completed_event import (
    CONTRACT_MERGE_COMPLETED_EVENT,
    ModelContractMergeCompletedEvent,
)
from omnibase_core.models.events.contract_validation.model_contract_merge_started_event import (
    CONTRACT_MERGE_STARTED_EVENT,
    ModelContractMergeStartedEvent,
)
from omnibase_core.models.events.contract_validation.model_contract_ref import (
    ModelContractRef,
)
from omnibase_core.models.events.contract_validation.model_contract_validation_context import (
    ModelContractValidationContext,
)
from omnibase_core.models.events.contract_validation.model_contract_validation_event_base import (
    ModelContractValidationEventBase,
)
from omnibase_core.models.events.contract_validation.model_contract_validation_failed_event import (
    CONTRACT_VALIDATION_FAILED_EVENT,
    ModelContractValidationFailedEvent,
)
from omnibase_core.models.events.contract_validation.model_contract_validation_passed_event import (
    CONTRACT_VALIDATION_PASSED_EVENT,
    ModelContractValidationPassedEvent,
)
from omnibase_core.models.events.contract_validation.model_contract_validation_started_event import (
    CONTRACT_VALIDATION_STARTED_EVENT,
    ModelContractValidationStartedEvent,
)

__all__ = [
    # Base and reference models
    "ModelContractRef",
    "ModelContractValidationContext",
    "ModelContractValidationEventBase",
    # Validation event models
    "ModelContractValidationStartedEvent",
    "ModelContractValidationPassedEvent",
    "ModelContractValidationFailedEvent",
    # Merge event models
    "ModelContractMergeStartedEvent",
    "ModelContractMergeCompletedEvent",
    # Event type constants
    "CONTRACT_VALIDATION_STARTED_EVENT",
    "CONTRACT_VALIDATION_PASSED_EVENT",
    "CONTRACT_VALIDATION_FAILED_EVENT",
    "CONTRACT_MERGE_STARTED_EVENT",
    "CONTRACT_MERGE_COMPLETED_EVENT",
]
