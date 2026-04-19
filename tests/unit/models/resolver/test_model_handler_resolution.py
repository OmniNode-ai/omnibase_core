# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Unit tests for ModelHandlerResolution (OMN-9195/OMN-9196).

Verifies:
- frozen + extra="forbid" config
- outcome is the only required field
- handler_instance defaults to None, skipped_handler/skipped_reason default ""
- all six EnumHandlerResolutionOutcome values are accepted
- skip-mode construction preserves handler name + reason text
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from omnibase_core.enums.enum_handler_resolution_outcome import (
    EnumHandlerResolutionOutcome,
)
from omnibase_core.models.resolver.model_handler_resolution import (
    ModelHandlerResolution,
)


@pytest.mark.unit
class TestModelHandlerResolutionFrozen:
    """Frozen + extra='forbid' config."""

    def test_resolution_is_frozen(self) -> None:
        res = ModelHandlerResolution(
            outcome=EnumHandlerResolutionOutcome.RESOLVED_VIA_NODE_REGISTRY,
            handler_instance=object(),
        )
        with pytest.raises(ValidationError):
            res.skipped_reason = "Mutated"  # type: ignore[misc]  # NOTE(OMN-9196): intentional assignment to frozen field verifies immutability enforcement

    def test_resolution_rejects_extra_fields(self) -> None:
        with pytest.raises(ValidationError):
            ModelHandlerResolution(
                outcome=EnumHandlerResolutionOutcome.RESOLVED_VIA_NODE_REGISTRY,
                handler_instance=object(),
                unknown_field="x",  # type: ignore[call-arg]  # NOTE(OMN-9196): intentional unknown kwarg verifies extra='forbid' rejection
            )


@pytest.mark.unit
class TestModelHandlerResolutionDefaults:
    """Default-value contract for optional fields on SKIP outcome.

    Note: the cross-field validator rejects non-skip outcomes without a
    handler_instance, and rejects skip outcomes without skip metadata. These
    tests therefore use the SKIP outcome (which permits default=None for
    handler_instance) and verify the default semantics of skipped_*
    via the minimal valid SKIP construction.
    """

    def test_handler_instance_defaults_none_on_skip(self) -> None:
        res = ModelHandlerResolution(
            outcome=EnumHandlerResolutionOutcome.RESOLVED_VIA_LOCAL_OWNERSHIP_SKIP,
            skipped_handler="HandlerFoo",
            skipped_reason="not hosted",
        )
        assert res.handler_instance is None

    def test_non_skip_requires_handler_instance(self) -> None:
        """Cross-field invariant: non-skip outcomes must carry an instance."""
        with pytest.raises(ValidationError):
            ModelHandlerResolution(
                outcome=EnumHandlerResolutionOutcome.RESOLVED_VIA_NODE_REGISTRY,
            )

    def test_skipped_handler_empty_on_successful_resolution(self) -> None:
        res = ModelHandlerResolution(
            outcome=EnumHandlerResolutionOutcome.RESOLVED_VIA_NODE_REGISTRY,
            handler_instance=object(),
        )
        assert res.skipped_handler == ""

    def test_skipped_reason_empty_on_successful_resolution(self) -> None:
        res = ModelHandlerResolution(
            outcome=EnumHandlerResolutionOutcome.RESOLVED_VIA_NODE_REGISTRY,
            handler_instance=object(),
        )
        assert res.skipped_reason == ""


@pytest.mark.unit
class TestModelHandlerResolutionRequiredFields:
    """`outcome` is the only required field."""

    def test_missing_outcome_raises(self) -> None:
        with pytest.raises(ValidationError):
            ModelHandlerResolution()  # type: ignore[call-arg]  # NOTE(OMN-9196): intentional missing required arg verifies outcome is mandatory


@pytest.mark.unit
class TestModelHandlerResolutionOutcomeAcceptsAllEnumValues:
    """Construction accepts every enum member (resolver may return any)."""

    @pytest.mark.parametrize("outcome", list(EnumHandlerResolutionOutcome))
    def test_accepts_every_outcome_member(
        self, outcome: EnumHandlerResolutionOutcome
    ) -> None:
        # Cross-field invariant: SKIP requires skip metadata; non-SKIP requires
        # handler_instance. Supply both so each enum value constructs successfully.
        if outcome == EnumHandlerResolutionOutcome.RESOLVED_VIA_LOCAL_OWNERSHIP_SKIP:
            res = ModelHandlerResolution(
                outcome=outcome,
                skipped_handler="HandlerFoo",
                skipped_reason="not hosted here",
            )
        else:
            res = ModelHandlerResolution(outcome=outcome, handler_instance=object())
        assert res.outcome is outcome


@pytest.mark.unit
class TestModelHandlerResolutionSkipMode:
    """Skip path carries handler identifier + reason text."""

    def test_skip_preserves_handler_and_reason(self) -> None:
        res = ModelHandlerResolution(
            outcome=EnumHandlerResolutionOutcome.RESOLVED_VIA_LOCAL_OWNERSHIP_SKIP,
            skipped_handler="HandlerFoo",
            skipped_reason="node_foo not hosted in this runtime",
        )
        assert (
            res.outcome
            == EnumHandlerResolutionOutcome.RESOLVED_VIA_LOCAL_OWNERSHIP_SKIP
        )
        assert res.skipped_handler == "HandlerFoo"
        assert res.skipped_reason == "node_foo not hosted in this runtime"
        assert res.handler_instance is None

    def test_resolved_mode_carries_handler_instance(self) -> None:
        sentinel_instance = object()
        res = ModelHandlerResolution(
            outcome=EnumHandlerResolutionOutcome.RESOLVED_VIA_NODE_REGISTRY,
            handler_instance=sentinel_instance,
        )
        assert res.handler_instance is sentinel_instance


@pytest.mark.unit
class TestModelHandlerResolutionOutcomeInvariants:
    """Cross-field validator: outcome dictates handler_instance + skip metadata.

    Per module docstring contract:
        - SKIP outcome: handler_instance MUST be None; skipped_* MUST be non-empty
        - Non-SKIP outcome: handler_instance MUST NOT be None; skipped_* MUST be empty
    """

    def test_skip_outcome_rejects_non_none_handler_instance(self) -> None:
        with pytest.raises(ValidationError):
            ModelHandlerResolution(
                outcome=EnumHandlerResolutionOutcome.RESOLVED_VIA_LOCAL_OWNERSHIP_SKIP,
                handler_instance=object(),
                skipped_handler="HandlerFoo",
                skipped_reason="not hosted",
            )

    def test_skip_outcome_rejects_empty_skipped_handler(self) -> None:
        with pytest.raises(ValidationError):
            ModelHandlerResolution(
                outcome=EnumHandlerResolutionOutcome.RESOLVED_VIA_LOCAL_OWNERSHIP_SKIP,
                skipped_reason="not hosted",
            )

    def test_skip_outcome_rejects_empty_skipped_reason(self) -> None:
        with pytest.raises(ValidationError):
            ModelHandlerResolution(
                outcome=EnumHandlerResolutionOutcome.RESOLVED_VIA_LOCAL_OWNERSHIP_SKIP,
                skipped_handler="HandlerFoo",
            )

    def test_non_skip_outcome_rejects_none_handler_instance(self) -> None:
        with pytest.raises(ValidationError):
            ModelHandlerResolution(
                outcome=EnumHandlerResolutionOutcome.RESOLVED_VIA_NODE_REGISTRY,
            )

    def test_non_skip_outcome_rejects_populated_skipped_handler(self) -> None:
        with pytest.raises(ValidationError):
            ModelHandlerResolution(
                outcome=EnumHandlerResolutionOutcome.RESOLVED_VIA_NODE_REGISTRY,
                handler_instance=object(),
                skipped_handler="HandlerFoo",
            )

    def test_non_skip_outcome_rejects_populated_skipped_reason(self) -> None:
        with pytest.raises(ValidationError):
            ModelHandlerResolution(
                outcome=EnumHandlerResolutionOutcome.RESOLVED_VIA_NODE_REGISTRY,
                handler_instance=object(),
                skipped_reason="not hosted",
            )


@pytest.mark.unit
class TestModelHandlerResolutionExportedFromPackage:
    """Re-export hygiene: model importable from `omnibase_core.models.resolver`."""

    def test_reexport_from_resolver_package(self) -> None:
        from omnibase_core.models.resolver import (
            ModelHandlerResolution as ReexportedRes,
        )

        assert ReexportedRes is ModelHandlerResolution


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
