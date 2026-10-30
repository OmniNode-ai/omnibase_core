# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Admission: installed file, trusted prefixes, lane profiles (OMN-21589, A1 AC7)."""

import pytest

from omnibase_core.enums.enum_announce_refusal_reason import EnumAnnounceRefusalReason
from tests.unit.models.nodes.package_announce.fixture_planted import (
    announcement,
    contract_bytes,
    policy,
)

Reason = EnumAnnounceRefusalReason


@pytest.mark.unit
def test_a_good_contract_is_admitted() -> None:
    raw = contract_bytes("control")
    assert policy().admit(announcement(raw, name="control"), raw).refusal_reason is None


@pytest.mark.unit
def test_planted_untrusted_handler_prefix_is_refused() -> None:
    raw = contract_bytes("planted", handler_module="rogue_pkg.nodes.planted.handler")
    result = policy().admit(announcement(raw, name="planted"), raw)
    assert result.refusal_reason is Reason.HANDLER_OUTSIDE_TRUSTED_PREFIXES


@pytest.mark.unit
def test_planted_unowned_profile_is_refused_and_an_owned_one_is_admitted() -> None:
    raw = contract_bytes("planted", profiles=("cloud_only",))
    refused = policy().admit(announcement(raw, name="planted"), raw)
    admitted = policy(profiles=("main", "cloud_only")).admit(
        announcement(raw, name="planted"), raw
    )
    assert refused.refusal_reason is Reason.PROFILE_NOT_OWNED
    assert admitted.refusal_reason is None


@pytest.mark.unit
def test_planted_missing_installed_file_is_refused() -> None:
    raw = contract_bytes("planted")
    result = policy().admit(announcement(raw, name="planted"), None)
    assert result.refusal_reason is Reason.INSTALLED_FILE_MISSING


@pytest.mark.unit
def test_planted_file_changed_after_announcement_fails_the_hash_check() -> None:
    announced = contract_bytes("planted")
    edited = announced + b"# edited after the announcement\n"
    result = policy().admit(announcement(announced, name="planted"), edited)
    assert result.refusal_reason is Reason.HASH_MISMATCH


@pytest.mark.unit
def test_the_checks_run_in_the_documented_order() -> None:
    """Both planted at once: the hash is checked before the prefix, the prefix before the profile."""
    raw = contract_bytes(
        "planted", handler_module="rogue_pkg.x", profiles=("cloud_only",)
    )
    record = announcement(raw, name="planted")
    assert policy().admit(record, raw + b"#").refusal_reason is Reason.HASH_MISMATCH
    assert (
        policy().admit(record, raw).refusal_reason
        is Reason.HANDLER_OUTSIDE_TRUSTED_PREFIXES
    )


@pytest.mark.unit
def test_the_same_inputs_give_the_same_reason_every_time() -> None:
    """Admission reads nothing but its arguments, so no bus can change its answer."""
    raw = contract_bytes("planted", handler_module="rogue_pkg.x")
    record = announcement(raw, name="planted")
    assert {policy().admit(record, raw).refusal_reason for _ in range(3)} == {
        Reason.HANDLER_OUTSIDE_TRUSTED_PREFIXES
    }
