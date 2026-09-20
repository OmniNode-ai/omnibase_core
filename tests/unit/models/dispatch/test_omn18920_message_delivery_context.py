# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""OMN-18920: the delivery-context model, step 1 of the OMN-18918 chain.

Inert by construction — nothing imports it until step 2 — so these tests are
the only thing standing behind it until then. They assert the three
properties the later steps rely on, rather than restating the field list.
"""

from __future__ import annotations

import subprocess
from datetime import UTC, datetime
from pathlib import Path

import pytest
from pydantic import ValidationError

from omnibase_core.models.dispatch import ModelMessageDeliveryContext

pytestmark = pytest.mark.unit

# Placed under tests/unit/models/dispatch/ to mirror the source tree, and
# NOT at the tests/ root: `test_detect_test_paths` pins the always-run set to
# exactly the non-unit test tree, so a unit test sitting at the root silently
# widens what every CI run executes. CI caught this on the first push.


def test_it_is_importable_from_the_dispatch_package_and_frozen() -> None:
    """AC1. Frozen is asserted, not declared in a docstring.

    A delivery already happened; nothing downstream has any business
    revising where it came from.
    """
    context = ModelMessageDeliveryContext(
        topic="onex.evt.omnibase-infra.runner-fleet.v1", partition=0, offset=16698
    )

    assert context.offset == 16698
    with pytest.raises(ValidationError):
        context.offset = 16699  # type: ignore[misc]


def test_an_absent_broker_time_stays_absent() -> None:
    """AC2. Never defaulted to a clock reading.

    A defaulted time here would let a consumer read the runtime's own wall
    clock as a broker fact — the same reason `_envelope_timestamp` is
    injected only when the producer actually recorded one.
    """
    without = ModelMessageDeliveryContext(topic="t", partition=0, offset=0)
    assert without.broker_timestamp is None

    stamped = datetime(2026, 9, 20, 15, 3, 9, tzinfo=UTC)
    with_time = ModelMessageDeliveryContext(
        topic="t", partition=0, offset=0, broker_timestamp=stamped
    )
    assert with_time.broker_timestamp == stamped


@pytest.mark.parametrize(
    ("partition", "offset"),
    [(-1, 0), (0, -1), (-1, -1)],
)
def test_negative_coordinates_are_refused(partition: int, offset: int) -> None:
    """AC3. A tolerated -1 is the shape a sentinel takes later.

    Kafka coordinates are non-negative by definition. Accepting a negative
    one means the first person who needs a "no value" marker reaches for it,
    and downstream it reads as a real coordinate.
    """
    with pytest.raises(ValidationError):
        ModelMessageDeliveryContext(topic="t", partition=partition, offset=offset)


def test_an_empty_topic_is_refused() -> None:
    """An offset is meaningless without the topic and partition it indexes."""
    with pytest.raises(ValidationError):
        ModelMessageDeliveryContext(topic="", partition=0, offset=0)


def test_an_unknown_field_is_refused() -> None:
    """`extra="forbid"`, so a typo at a call site fails loudly rather than
    silently carrying nothing."""
    with pytest.raises(ValidationError):
        ModelMessageDeliveryContext(
            topic="t",
            partition=0,
            offset=0,
            partion=1,  # type: ignore[call-arg]
        )


def test_this_step_is_inert_nothing_imports_it_yet() -> None:
    """AC4. The claim that makes this step safe to land on its own.

    If a later step lands out of order, or someone wires it early, this
    turns red rather than letting a half-wired chain look complete.
    """
    from omnibase_core.validators.no_unguarded_git_subprocess import (
        scrub_git_location_env,
    )

    repo_root = Path(__file__).resolve().parents[4]
    # env= is not optional here (OMN-14891): git exports GIT_DIR and
    # GIT_WORK_TREE into every hook environment and they OVERRIDE `cwd=`, so
    # under a pre-push hook this walk would silently search the wrong tree
    # and the inertness claim would pass against nothing.
    found = subprocess.run(
        ["git", "grep", "-l", "ModelMessageDeliveryContext"],
        cwd=repo_root,
        capture_output=True,
        text=True,
        check=False,
        env=scrub_git_location_env(),
    )
    # Untracked-but-staged files are included by git grep against the index;
    # an empty result would mean the walk itself is broken, so require ours.
    referencing = {line for line in found.stdout.split("\n") if line}
    assert referencing, "git grep found nothing at all — the walk is inert"
    assert referencing == {
        "src/omnibase_core/models/dispatch/__init__.py",
        "src/omnibase_core/models/dispatch/model_message_delivery_context.py",
        "tests/unit/models/dispatch/test_omn18920_message_delivery_context.py",
    }, sorted(referencing)
