# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""
Cross-repo validation event models.

This module provides event models for cross-repo validation lifecycle events
in the ONEX framework. These events enable tracking, replay, and dashboard
integration for validation operations.

Event Lifecycle:
    started -> violations batch(es)* -> completed

Event Types:
    - ``onex.evt.validation.cross-repo-run-started.v1``: Validation run begins
    - ``onex.evt.validation.cross-repo-violations-batch.v1``: Batch of violations
    - ``onex.evt.validation.cross-repo-run-completed.v1``: Validation run completes

Import Example:
    .. code-block:: python

        from omnibase_core.models.events.validation import (
            # Base model
            ModelValidationEventBase,
            # Event models
            ModelValidationRunStartedEvent,
            ModelValidationViolationsBatchEvent,
            ModelValidationRunCompletedEvent,
            # Violation record for batches
            ModelViolationRecord,
            # Event type constants
            VALIDATION_RUN_STARTED_EVENT,
            VALIDATION_VIOLATIONS_BATCH_EVENT,
            VALIDATION_RUN_COMPLETED_EVENT,
        )

Usage Example:
    .. code-block:: python

        from uuid import uuid4
        from datetime import datetime, UTC
        from omnibase_core.models.events.validation import (
            ModelValidationRunStartedEvent,
            ModelValidationRunCompletedEvent,
        )

        # Start validation
        run_id = uuid4()
        started_event = ModelValidationRunStartedEvent.create(
            run_id=run_id,
            repo_id="omnibase_core",
            root_path="/workspace/omnibase_core",
            policy_name="omnibase_core_policy",
            started_at=datetime.now(UTC),
            rules_enabled=("repo_boundaries", "forbidden_imports"),
        )

        # ... perform validation and emit violation batches ...

        # Complete validation
        completed_event = ModelValidationRunCompletedEvent.create(
            run_id=run_id,  # Same run_id for lifecycle correlation
            repo_id="omnibase_core",
            is_valid=True,
            total_violations=0,
            error_count=0,
            warning_count=0,
            suppressed_count=0,
            files_processed=150,
            rules_applied=5,
            duration_ms=1250,
            completed_at=datetime.now(UTC),
        )

See Also:
    - :mod:`omnibase_core.validation.cross_repo`: Validation engine
    - :mod:`omnibase_core.nodes.validation`: Orchestrator node

.. versionadded:: 0.13.0
    Initial implementation as part of OMN-1776 cross-repo orchestrator.
"""

from omnibase_core.models.events.validation.model_validation_event_base import (
    ModelValidationEventBase,
)
from omnibase_core.models.events.validation.model_validation_run_completed_event import (
    VALIDATION_RUN_COMPLETED_EVENT,
    ModelValidationRunCompletedEvent,
)
from omnibase_core.models.events.validation.model_validation_run_started_event import (
    VALIDATION_RUN_STARTED_EVENT,
    ModelValidationRunStartedEvent,
)
from omnibase_core.models.events.validation.model_validation_violations_batch_event import (
    VALIDATION_VIOLATIONS_BATCH_EVENT,
    ModelValidationViolationsBatchEvent,
)
from omnibase_core.models.events.validation.model_violation_record import (
    ModelViolationRecord,
)

__all__ = [
    # Base model
    "ModelValidationEventBase",
    # Event models
    "ModelValidationRunStartedEvent",
    "ModelValidationViolationsBatchEvent",
    "ModelValidationRunCompletedEvent",
    # Violation record
    "ModelViolationRecord",
    # Event type constants
    "VALIDATION_RUN_STARTED_EVENT",
    "VALIDATION_VIOLATIONS_BATCH_EVENT",
    "VALIDATION_RUN_COMPLETED_EVENT",
]
