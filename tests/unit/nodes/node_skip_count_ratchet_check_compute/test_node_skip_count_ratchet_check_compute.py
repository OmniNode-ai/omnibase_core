# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""Direct pure-handler parity for counts, identities and empty inventories."""

from __future__ import annotations

from typing import Literal

import pytest
from pydantic import ValidationError

from omnibase_core.models.nodes.skip_count_ratchet_check.model_skip_count_baseline_entry import (
    ModelSkipCountBaselineEntry,
)
from omnibase_core.models.nodes.skip_count_ratchet_check.model_skip_count_observation import (
    ModelSkipCountObservation,
)
from omnibase_core.models.nodes.skip_count_ratchet_check.model_skip_count_ratchet_check_input import (
    ModelSkipCountRatchetCheckInput,
)
from omnibase_core.models.nodes.skip_count_ratchet_check.model_skip_count_record import (
    ModelSkipCountRecord,
)
from omnibase_core.nodes.node_skip_count_ratchet_check_compute.handler import (
    NodeSkipCountRatchetCheckCompute,
)

pytestmark = pytest.mark.unit


def request(
    mode: Literal["count", "nodeids"], identities: tuple[str, ...], collected: int = 100
) -> ModelSkipCountRatchetCheckInput:
    baseline = ModelSkipCountBaselineEntry(
        key="fixture/" + mode,
        repo="r",
        job="j",
        mode=mode,
        max_skips=2,
        baseline_collected=100,
        node_ids=frozenset({"pkg.a::test_one", "pkg.b::test_two"}),
        path="recorded.yaml",
    )
    observed = ModelSkipCountObservation(
        records=tuple(
            ModelSkipCountRecord(identity=i, skipped=True) for i in identities
        ),
        collected=collected,
        files=1,
    )
    return ModelSkipCountRatchetCheckInput(baseline=baseline, observation=observed)


@pytest.mark.parametrize("mode", ["count", "nodeids"])
def test_parity_handler_growth(mode: Literal["count", "nodeids"]) -> None:
    value = request(mode, ("pkg.a::test_one", "pkg.b::test_two", "pkg.c::test_new"))
    report = NodeSkipCountRatchetCheckCompute().handle(value)
    assert report.overall_status == "FAIL"
    assert len(report.findings) == 2
    assert report.findings[1].message == "    + pkg.c::test_new"
    assert all(f.rule_id == "skip-growth-" + mode for f in report.findings)
    assert report.provenance.validators_run == ("skip-count-ratchet",)


@pytest.mark.parametrize("mode", ["count", "nodeids"])
def test_parity_handler_prefix_deduplication(mode: Literal["count", "nodeids"]) -> None:
    value = request(
        mode, ("tests.pkg.a::test_one", "pkg.a::test_one", "tests.pkg.b::test_two")
    )
    assert value.observation.count == 2
    assert NodeSkipCountRatchetCheckCompute().handle(value).overall_status == "PASS"


def test_parity_handler_narrow_selection_new_id_still_fails() -> None:
    assert (
        NodeSkipCountRatchetCheckCompute()
        .handle(request("nodeids", ("pkg.c::test_new",), 40))
        .overall_status
        == "FAIL"
    )
    assert (
        NodeSkipCountRatchetCheckCompute()
        .handle(request("count", ("pkg.c::test_new",), 40))
        .overall_status
        == "PASS"
    )


def test_parity_handler_zero_records_error() -> None:
    report = NodeSkipCountRatchetCheckCompute().handle(request("count", (), 0))
    assert report.overall_status == "ERROR"
    assert report.findings[0].rule_id == "zero-test-records"


def test_parity_handler_models_frozen_and_extra_forbidden() -> None:
    value = request("count", ("pkg.a::test_one",))
    with pytest.raises(ValidationError):
        value.observation.collected = 1000
    with pytest.raises(ValidationError):
        ModelSkipCountRatchetCheckInput.model_validate(
            {**value.model_dump(), "override": True}
        )
