# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Unit tests for the demand-aware liveness registry and receipt contracts.

OMN-15126 implementation of the OMN-14845 design. Covers per-state required
field enforcement on ``ModelLivenessReceipt`` for all five states, and the
registry entry's ``effective_error_budget_ratio`` None==0.0 default.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import uuid4

import pytest
from pydantic import ValidationError

from omnibase_core.enums.enum_liveness_state import EnumLivenessState
from omnibase_core.models.runtime.model_demand_source_ref import ModelDemandSourceRef
from omnibase_core.models.runtime.model_event_ref import ModelEventRef
from omnibase_core.models.runtime.model_liveness_artifact_ref import ModelArtifactRef
from omnibase_core.models.runtime.model_liveness_receipt import ModelLivenessReceipt
from omnibase_core.models.runtime.model_liveness_registry_entry import (
    ModelLivenessRegistryEntry,
)
from omnibase_core.models.runtime.model_output_join_spec import ModelOutputJoinSpec
from omnibase_core.models.runtime.model_sampling_policy import ModelSamplingPolicy

pytestmark = pytest.mark.unit


def _event_ref(offset: int = 0) -> ModelEventRef:
    return ModelEventRef(
        topic="onex.evt.omnimarket.surface-demand.v1",
        partition=0,
        offset=offset,
        event_id=uuid4(),
    )


def _receipt_kwargs(**overrides: Any) -> dict[str, Any]:
    base: dict[str, Any] = {
        "receipt_id": uuid4(),
        "surface_id": "omnimarket.node_liveness_evaluate_compute",
        "lane": "dev",
        "deployed_sha": "abc1234",
        "image_digest": "sha256:deadbeef",
        "config_digest": "sha256:cafef00d",
        "evaluated_at": datetime.now(UTC),
        "freshness_window_seconds": 3600,
        "runner": "node_liveness_evaluate_compute",
        "demand_synthetic": False,
    }
    base.update(overrides)
    return base


class TestModelLivenessReceiptNotReady:
    def test_not_ready_requires_reason(self) -> None:
        with pytest.raises(ValidationError, match="not_ready_reason"):
            ModelLivenessReceipt(**_receipt_kwargs(state=EnumLivenessState.NOT_READY))

    def test_not_ready_valid(self) -> None:
        receipt = ModelLivenessReceipt(
            **_receipt_kwargs(
                state=EnumLivenessState.NOT_READY,
                not_ready_reason="registry entry unresolvable for surface_id",
            )
        )
        assert receipt.state == EnumLivenessState.NOT_READY
        assert receipt.correlation_id is None

    def test_not_ready_rejects_empty_reason(self) -> None:
        with pytest.raises(ValidationError, match="not_ready_reason"):
            ModelLivenessReceipt(
                **_receipt_kwargs(
                    state=EnumLivenessState.NOT_READY,
                    not_ready_reason="",
                )
            )

    def test_not_ready_forbids_healthy_only_fields(self) -> None:
        with pytest.raises(ValidationError, match="correlation_id"):
            ModelLivenessReceipt(
                **_receipt_kwargs(
                    state=EnumLivenessState.NOT_READY,
                    not_ready_reason="unresolvable",
                    correlation_id=uuid4(),
                )
            )


class TestModelLivenessReceiptNoDemand:
    def test_no_demand_requires_query_evidence(self) -> None:
        with pytest.raises(ValidationError, match="demand_query_evidence"):
            ModelLivenessReceipt(**_receipt_kwargs(state=EnumLivenessState.NO_DEMAND))

    def test_no_demand_valid(self) -> None:
        receipt = ModelLivenessReceipt(
            **_receipt_kwargs(
                state=EnumLivenessState.NO_DEMAND,
                demand_query_evidence="row_count=0 query_hash=sha256:...",
            )
        )
        assert receipt.state == EnumLivenessState.NO_DEMAND
        assert receipt.demand_query_evidence is not None

    def test_no_demand_rejects_empty_query_evidence(self) -> None:
        with pytest.raises(ValidationError, match="demand_query_evidence"):
            ModelLivenessReceipt(
                **_receipt_kwargs(
                    state=EnumLivenessState.NO_DEMAND,
                    demand_query_evidence="",
                )
            )


class TestModelLivenessReceiptHealthy:
    def test_healthy_requires_full_join(self) -> None:
        with pytest.raises(ValidationError):
            ModelLivenessReceipt(**_receipt_kwargs(state=EnumLivenessState.HEALTHY))

    def test_healthy_valid_full_join(self) -> None:
        input_ref = _event_ref(offset=10)
        terminal_ref = _event_ref(offset=11)
        receipt = ModelLivenessReceipt(
            **_receipt_kwargs(
                state=EnumLivenessState.HEALTHY,
                correlation_id=uuid4(),
                input_event_ref=input_ref,
                terminal_event_ref=terminal_ref,
                projection_key_canonical='{"correlation_id":"abc"}',
                projection_value_hash="sha256:observed",
                projection_expected_value_hash="sha256:expected",
                expected_value_predicate_result=True,
                checked_count=1,
                failed_count=0,
                failed_ratio=0.0,
            )
        )
        assert receipt.state == EnumLivenessState.HEALTHY
        assert receipt.input_event_ref == input_ref
        assert receipt.terminal_event_ref == terminal_ref

    def test_healthy_requires_projection_value_hash(self) -> None:
        with pytest.raises(ValidationError, match="projection_value_hash"):
            ModelLivenessReceipt(
                **_receipt_kwargs(
                    state=EnumLivenessState.HEALTHY,
                    correlation_id=uuid4(),
                    input_event_ref=_event_ref(),
                    terminal_event_ref=_event_ref(offset=1),
                    projection_key_canonical="k",
                    projection_expected_value_hash="sha256:expected",
                    expected_value_predicate_result=True,
                    checked_count=1,
                    failed_count=0,
                    failed_ratio=0.0,
                )
            )

    def test_healthy_requires_checked_count_at_least_one(self) -> None:
        with pytest.raises(ValidationError, match="checked_count must be >= 1"):
            ModelLivenessReceipt(
                **_receipt_kwargs(
                    state=EnumLivenessState.HEALTHY,
                    correlation_id=uuid4(),
                    input_event_ref=_event_ref(),
                    terminal_event_ref=_event_ref(offset=1),
                    projection_key_canonical="k",
                    projection_value_hash="sha256:observed",
                    projection_expected_value_hash="sha256:expected",
                    expected_value_predicate_result=True,
                    checked_count=0,
                    failed_count=0,
                    failed_ratio=0.0,
                )
            )

    def test_healthy_rejects_mismatched_failed_ratio(self) -> None:
        with pytest.raises(ValidationError, match="failed_ratio"):
            ModelLivenessReceipt(
                **_receipt_kwargs(
                    state=EnumLivenessState.HEALTHY,
                    correlation_id=uuid4(),
                    input_event_ref=_event_ref(),
                    terminal_event_ref=_event_ref(offset=1),
                    projection_key_canonical="k",
                    projection_value_hash="sha256:observed",
                    projection_expected_value_hash="sha256:expected",
                    expected_value_predicate_result=True,
                    checked_count=2,
                    failed_count=1,
                    failed_ratio=0.0,  # should be 0.5
                )
            )


class TestModelLivenessReceiptRed:
    def test_red_permits_missing_terminal_with_failure_detail(self) -> None:
        receipt = ModelLivenessReceipt(
            **_receipt_kwargs(
                state=EnumLivenessState.RED,
                correlation_id=uuid4(),
                input_event_ref=_event_ref(),
                projection_key_canonical="k",
                expected_value_predicate_result=False,
                checked_count=3,
                failed_count=1,
                failed_ratio=1 / 3,
                failure_detail="terminal event never observed within freshness window",
            )
        )
        assert receipt.state == EnumLivenessState.RED
        assert receipt.terminal_event_ref is None

    def test_red_permits_projection_value_hash(self) -> None:
        receipt = ModelLivenessReceipt(
            **_receipt_kwargs(
                state=EnumLivenessState.RED,
                correlation_id=uuid4(),
                input_event_ref=_event_ref(),
                projection_key_canonical="k",
                projection_value_hash="sha256:observed-but-mismatched",
                expected_value_predicate_result=False,
                checked_count=1,
                failed_count=1,
                failed_ratio=1.0,
                failure_detail="expected_value_predicate_result was False",
            )
        )
        assert receipt.projection_value_hash == "sha256:observed-but-mismatched"

    def test_red_requires_failure_detail(self) -> None:
        with pytest.raises(ValidationError, match="failure_detail"):
            ModelLivenessReceipt(
                **_receipt_kwargs(
                    state=EnumLivenessState.RED,
                    correlation_id=uuid4(),
                    input_event_ref=_event_ref(),
                    projection_key_canonical="k",
                    expected_value_predicate_result=False,
                    checked_count=1,
                    failed_count=1,
                    failed_ratio=1.0,
                )
            )


class TestModelLivenessReceiptStale:
    def test_stale_valid_with_no_prior_healthy(self) -> None:
        receipt = ModelLivenessReceipt(**_receipt_kwargs(state=EnumLivenessState.STALE))
        assert receipt.state == EnumLivenessState.STALE
        assert receipt.last_healthy_receipt_id is None

    def test_stale_valid_with_stale_prior_healthy(self) -> None:
        """A prior HEALTHY older than freshness_window_seconds -> STALE is valid."""
        now = datetime.now(UTC)
        receipt = ModelLivenessReceipt(
            **_receipt_kwargs(
                state=EnumLivenessState.STALE,
                evaluated_at=now,
                freshness_window_seconds=3600,
                last_healthy_receipt_id=uuid4(),
                last_healthy_at=now - timedelta(hours=2),
            )
        )
        assert receipt.last_healthy_receipt_id is not None

    def test_stale_rejects_prior_healthy_still_fresh(self) -> None:
        """A prior HEALTHY still inside freshness_window_seconds contradicts STALE (-> NO_DEMAND instead)."""
        now = datetime.now(UTC)
        with pytest.raises(ValidationError, match="contradicts a prior HEALTHY"):
            ModelLivenessReceipt(
                **_receipt_kwargs(
                    state=EnumLivenessState.STALE,
                    evaluated_at=now,
                    freshness_window_seconds=3600,
                    last_healthy_receipt_id=uuid4(),
                    last_healthy_at=now - timedelta(minutes=5),
                )
            )

    def test_stale_requires_last_healthy_at_alongside_id(self) -> None:
        with pytest.raises(ValidationError, match="must be provided together"):
            ModelLivenessReceipt(
                **_receipt_kwargs(
                    state=EnumLivenessState.STALE,
                    last_healthy_receipt_id=uuid4(),
                )
            )

    def test_stale_requires_last_healthy_receipt_id_alongside_at(self) -> None:
        with pytest.raises(ValidationError, match="must be provided together"):
            ModelLivenessReceipt(
                **_receipt_kwargs(
                    state=EnumLivenessState.STALE,
                    last_healthy_at=datetime.now(UTC) - timedelta(hours=2),
                )
            )

    def test_non_stale_forbids_last_healthy_fields(self) -> None:
        with pytest.raises(ValidationError, match="last_healthy_receipt_id"):
            ModelLivenessReceipt(
                **_receipt_kwargs(
                    state=EnumLivenessState.NOT_READY,
                    not_ready_reason="x",
                    last_healthy_receipt_id=uuid4(),
                    last_healthy_at=datetime.now(UTC),
                )
            )


class TestModelLivenessRegistryEntry:
    def _entry_kwargs(self, **overrides: Any) -> dict[str, Any]:
        base: dict[str, Any] = {
            "surface_id": "omnimarket.node_liveness_evaluate_compute",
            "owner": "platform-team",
            "lane": "dev",
            "demand_source": ModelDemandSourceRef(
                kind="table_query",
                locator="onex_liveness_demand.eligible_surface_demand",
                eligibility_predicate="surface_id = :surface_id",
            ),
            "expected_output_join": ModelOutputJoinSpec(
                terminal_topic="onex.evt.omnimarket.liveness-evaluated.v1",
                projection_table="onex_liveness.receipts",
                projection_key_fields=("surface_id", "correlation_id"),
                projection_key_canonicalization="json_sorted_keys",
                expected_value_predicate="state == 'healthy'",
            ),
            "artifact_ref": ModelArtifactRef(
                repo="OmniNode-ai/omnimarket",
                contract_path="src/omnimarket/nodes/node_liveness_evaluate_compute/contract.yaml",
            ),
            "freshness_slo_seconds": 3600,
        }
        base.update(overrides)
        return base

    def test_effective_error_budget_ratio_defaults_to_zero(self) -> None:
        entry = ModelLivenessRegistryEntry(**self._entry_kwargs())
        assert entry.error_budget_ratio is None
        assert entry.effective_error_budget_ratio == 0.0

    def test_effective_error_budget_ratio_honors_explicit_value(self) -> None:
        entry = ModelLivenessRegistryEntry(**self._entry_kwargs(error_budget_ratio=0.1))
        assert entry.effective_error_budget_ratio == 0.1

    def test_sampling_policy_none_by_default(self) -> None:
        entry = ModelLivenessRegistryEntry(**self._entry_kwargs())
        assert entry.sampling_policy is None

    def test_sampling_policy_explicit_opt_in(self) -> None:
        entry = ModelLivenessRegistryEntry(
            **self._entry_kwargs(
                sampling_policy=ModelSamplingPolicy(
                    strategy="deterministic_hash_stride",
                    min_sample_size=10,
                    max_eligible_volume_before_sampling=1000,
                )
            )
        )
        assert entry.sampling_policy is not None
        assert entry.sampling_policy.strategy == "deterministic_hash_stride"

    def test_registry_entry_is_frozen(self) -> None:
        entry = ModelLivenessRegistryEntry(**self._entry_kwargs())
        # Frozen-model mutation rejection: assert broadly (not pinned to
        # ValidationError) since the exact exception type Pydantic raises for
        # a frozen-field assignment is an implementation detail — the
        # behavior under test is immutability, not a specific exception class.
        with pytest.raises(Exception):
            # NOTE(OMN-15126): mypy correctly flags this assignment as an error
            # on a frozen model — that IS the behavior under test.
            entry.owner = "someone-else"  # type: ignore[misc]

    def test_registry_entry_forbids_extra_fields(self) -> None:
        with pytest.raises(ValidationError):
            # NOTE(OMN-15126): mypy correctly flags this as an unknown kwarg —
            # that IS the extra="forbid" behavior under test.
            ModelLivenessRegistryEntry(**self._entry_kwargs(), unexpected_field="x")  # type: ignore[call-arg]
