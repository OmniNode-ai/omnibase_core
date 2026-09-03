# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""``tenant-projection`` is a registered, consumer-attached lane (OMN-17556).

Eight TENANT-domain projection contracts (seven on ``main``, one on
``effects``) resolve the ``tenant_projection`` topology binding, whose
principal is ``tenant_projection_writer``. The shared runtime pods hold no
credential for that principal and -- by operator ruling, 2026-09-03 -- never
will: no credential env var on any shared pod. Those eight contracts therefore
move to ONE consolidated writer process running ``RUNTIME_PROFILE=
tenant-projection``, which is the only process that resolves the binding.

Two registry facts make that move safe, and this module pins both:

1. ``REGISTERED_RUNTIME_PROFILES`` must contain the name, or
   ``ValidatorRuntimeProfiles._check_unregistered`` rejects every one of the
   eight contracts at commit/CI time.
2. ``CONSUMER_ATTACHED_RUNTIME_PROFILES`` must contain it too. All eight are
   subscribing REDUCER/EFFECT contracts naming ONLY this profile, so a
   registered-but-not-consumer-attached name would pass check 1 and then trip
   ``_check_no_consumer_lane`` -- the subtler silent-orphan class where the
   name is legal but no process ever drains the subscriptions.

The writer really does attach a consumer group (it is the ONEX runtime booted
under a different profile, not a bespoke daemon), so membership in the second
set is a statement of fact about the deployed process, not a validator
workaround.
"""

from __future__ import annotations

import pytest

from omnibase_core.constants.constants_runtime_profiles import (
    CONSUMER_ATTACHED_RUNTIME_PROFILES,
    REGISTERED_RUNTIME_PROFILES,
)

pytestmark = pytest.mark.unit

_TENANT_PROJECTION = "tenant-projection"


def test_tenant_projection_is_registered() -> None:
    assert _TENANT_PROJECTION in REGISTERED_RUNTIME_PROFILES


def test_tenant_projection_is_consumer_attached() -> None:
    assert _TENANT_PROJECTION in CONSUMER_ATTACHED_RUNTIME_PROFILES


def test_consumer_attached_stays_a_subset_of_registered() -> None:
    """The invariant the two sets exist to express, re-asserted after the add."""
    assert CONSUMER_ATTACHED_RUNTIME_PROFILES <= REGISTERED_RUNTIME_PROFILES


def test_no_underscore_variant_is_registered() -> None:
    """Profile names are hyphenated; an underscore twin would orphan silently.

    ``tenant_projection`` (underscore) is the BINDING name in the topology and
    ``tenant-projection`` (hyphen) is the RUNTIME PROFILE. They are adjacent
    strings with different meanings, and a contract that names the binding
    where it means the profile would be unregistered -- caught loudly by
    ``_check_unregistered`` only as long as the underscore form never becomes
    a registered alias.
    """
    assert "tenant_projection" not in REGISTERED_RUNTIME_PROFILES
