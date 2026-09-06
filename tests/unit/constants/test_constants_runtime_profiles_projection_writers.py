# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""The seven standalone projection writers are registered lanes (OMN-17985).

Seven Deployments run on ``onex-dev`` under ``RUNTIME_PROFILE`` values that
neither registry in this module knew and that no contract declared:
``projection-writer-{delegation,hook-ledger,live-events,registration,savings,
tenant-credentials,tenant-registry}``. Each is a standalone
``python -m <handler>`` ``BaseProjectionRunner`` process with its own explicit
``KAFKA_CONSUMER_GROUP``.

Why REGISTER rather than RETIRE, per writer, on measured evidence (probe run
``34026361940``, dev-system ``i-06169517a92b45f86``, namespace ``onex-dev``):
all seven are ``1/1`` Ready with zero restarts, all seven joined their consumer
group, and the group coordinator issued each a real partition assignment --
delegation 9 partitions, hook-ledger 4, live-events 28, registration 3,
savings 5, tenant-credentials 2, tenant-registry 1. ``public.live_events`` held
291,415 rows and grew between two runs 28 minutes apart, so the archetype
demonstrably materializes. Retiring any of the seven would delete a live
consumer of topics no other process drains; none owns nothing.

The name being unregistered was inert only by accident of archetype --
``omnimarket/src/omnimarket/projection/runner.py`` never reads
``RUNTIME_PROFILE``. For a runtime-HOSTED contract the same unregistered name
is the OMN-12950 orphan mechanism exactly: the auto-wiring ownership filter
matches no declared list and is ``!= "main"``, so every contract is skipped and
the process wires nothing while staying Ready.

Registration is what makes the ownership claim single-valued. Until these names
existed, each writer's contract was ALSO owned by a shared runtime -- the two
declaring ``[effects]`` by the effects pod, the five declaring nothing or ``[]``
by ``main`` -- so two processes claimed the same subscriptions under different
consumer groups. Naming the writer's own profile on its contract is what
removes the second claimant.

Both sets, per name, deliberately:

1. ``REGISTERED_RUNTIME_PROFILES`` -- or ``_check_unregistered`` rejects the
   contract declaration at commit/CI time.
2. ``CONSUMER_ATTACHED_RUNTIME_PROFILES`` -- every one of the seven contracts is
   a subscribing projection archetype naming ONLY its writer profile, so a
   registered-but-unattached name would pass check 1 and trip
   ``_check_no_consumer_lane``. Membership is a statement of measured fact
   about a deployed process that holds a broker-issued partition assignment,
   not a validator workaround.
"""

from __future__ import annotations

import pytest

from omnibase_core.constants.constants_runtime_profiles import (
    CONSUMER_ATTACHED_RUNTIME_PROFILES,
    REGISTERED_RUNTIME_PROFILES,
)

pytestmark = pytest.mark.unit

PROJECTION_WRITER_PROFILES: tuple[str, ...] = (
    "projection-writer-delegation",
    "projection-writer-hook-ledger",
    "projection-writer-live-events",
    "projection-writer-registration",
    "projection-writer-savings",
    "projection-writer-tenant-credentials",
    "projection-writer-tenant-registry",
)


@pytest.mark.parametrize("profile", PROJECTION_WRITER_PROFILES)
def test_projection_writer_profile_is_registered(profile: str) -> None:
    assert profile in REGISTERED_RUNTIME_PROFILES


@pytest.mark.parametrize("profile", PROJECTION_WRITER_PROFILES)
def test_projection_writer_profile_is_consumer_attached(profile: str) -> None:
    """Each writer attaches a group and drains the topics its contract names."""
    assert profile in CONSUMER_ATTACHED_RUNTIME_PROFILES


def test_consumer_attached_stays_a_subset_of_registered() -> None:
    """The invariant the two sets exist to express, re-asserted after the add."""
    assert CONSUMER_ATTACHED_RUNTIME_PROFILES <= REGISTERED_RUNTIME_PROFILES


@pytest.mark.parametrize("profile", PROJECTION_WRITER_PROFILES)
def test_no_underscore_variant_is_registered(profile: str) -> None:
    """Profile names are hyphenated; an underscore twin would orphan silently.

    The deployed env values are hyphenated. An underscore spelling is a
    different string that no registry knows, and admitting it as an alias would
    convert ``_check_unregistered`` from a loud refusal into a silent pass.
    """
    assert profile.replace("-", "_") not in REGISTERED_RUNTIME_PROFILES


def test_every_registered_name_is_hyphen_lowercase() -> None:
    """Normalization is ``strip().lower()``; a name that is not already in that
    form can never be matched by the ownership filter or the validator."""
    for profile in REGISTERED_RUNTIME_PROFILES:
        assert profile == profile.strip().lower()
        assert "_" not in profile
