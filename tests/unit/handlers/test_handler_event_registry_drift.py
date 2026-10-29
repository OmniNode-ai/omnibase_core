# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""Direct tests of the event-registry drift handler (OMN-21416).

The CLI refuses an empty source before it reaches the handler, so these cover
the handler's own guard for callers that build the typed input themselves.
"""

from __future__ import annotations

import pytest

from omnibase_core.handlers.handler_event_registry_drift import (
    HandlerEventRegistryDrift,
)
from omnibase_core.models.event_registry_drift.model_event_registration import (
    ModelEventRegistration,
)
from omnibase_core.models.event_registry_drift.model_event_registry_drift_check_input import (
    ModelEventRegistryDriftCheckInput,
)

pytestmark = pytest.mark.unit

_USAGE = ModelEventRegistration(
    event_type="delegation.usage_call",
    topics=("onex.evt.omnimarket.delegation-usage-call.v1",),
    partition_key_field="tenant_id",
    required_fields=("call_id", "tenant_id"),
    source="registry.yaml",
)


@pytest.mark.parametrize(
    ("source", "registry"),
    [((), (_USAGE,)), ((_USAGE,), ())],
    ids=["empty_source_side", "empty_registry_side"],
)
def test_an_empty_side_is_error_never_pass(
    source: tuple[ModelEventRegistration, ...],
    registry: tuple[ModelEventRegistration, ...],
) -> None:
    report = HandlerEventRegistryDrift().handle(
        ModelEventRegistryDriftCheckInput(
            source_registrations=source, registry_registrations=registry
        )
    )
    assert report.overall_status == "ERROR"
    assert [f.rule_id for f in report.findings] == ["empty_source"]
