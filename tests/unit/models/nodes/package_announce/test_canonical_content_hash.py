# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""The canonical content hash is the declared form and nothing else (OMN-21589, A1 AC1)."""

import hashlib

import pytest

from omnibase_core.models.events.contract_registration.model_node_announcement import (
    ModelNodeAnnouncement,
)
from tests.unit.models.nodes.package_announce.fixture_planted import contract_bytes

hash_of = ModelNodeAnnouncement.canonical_content_hash


@pytest.mark.unit
def test_matches_an_independent_restatement_of_the_declared_form() -> None:
    raw = contract_bytes("example")
    assert hash_of(raw) == hashlib.sha256(raw).hexdigest()


@pytest.mark.unit
def test_windows_and_unix_line_endings_hash_alike() -> None:
    unix = contract_bytes("example")
    windows = contract_bytes("example", newline="\r\n")
    assert b"\r\n" in windows and b"\r" not in unix
    assert hash_of(windows) == hash_of(unix), (
        "falsifier: a hash that differs from the canonical form's"
    )
    assert hash_of(windows) != hashlib.sha256(windows).hexdigest()


@pytest.mark.unit
def test_a_lone_carriage_return_is_a_line_ending_too() -> None:
    assert hash_of(b"a: 1\rb: 2\r") == hash_of(b"a: 1\nb: 2\n")


@pytest.mark.unit
def test_planted_whitespace_edit_moves_the_hash() -> None:
    """The form hashes raw bytes, so a whitespace-only edit is a visible, cheap false positive."""
    raw = contract_bytes("example")
    assert hash_of(raw + b"\n") != hash_of(raw)
    assert hash_of(
        raw.replace(b"node_type: compute", b"node_type:  compute")
    ) != hash_of(raw)


@pytest.mark.unit
def test_is_64_lowercase_hex_with_no_prefix() -> None:
    digest = hash_of(b"")
    assert len(digest) == 64 and digest == digest.lower()
    assert set(digest) <= set("0123456789abcdef")
