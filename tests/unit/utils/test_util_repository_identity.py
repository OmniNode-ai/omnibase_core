# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Tests for canonical repository storage partition keys."""

from __future__ import annotations

import pytest

from omnibase_core.errors.model_onex_error import ModelOnexError
from omnibase_core.utils.util_repository_identity import (
    canonical_repository_partition_key,
)

# This mirrors the explicit ASCII owner/repository CHECK used by Market's
# goal-attempt SQL migrations. Keep it in sync with both durable tables.
SQL_REPOSITORY_CHECK_PATTERN = (
    r"^[A-Za-z0-9][A-Za-z0-9_.-]*/[A-Za-z0-9][A-Za-z0-9_.-]*$"
)


@pytest.mark.parametrize(
    ("repository", "expected_key"),
    [
        ("OmniNode-ai/OmniMarket", "omninode-ai/omnimarket"),
        ("OMNINODE-AI/OMNIMARKET", "omninode-ai/omnimarket"),
        ("OmniNode-ai/OmniBase_Core", "omninode-ai/omnibase_core"),
    ],
)
def test_partition_key_matches_sql_lower_for_ascii_spellings(
    repository: str, expected_key: str
) -> None:
    assert canonical_repository_partition_key(repository) == expected_key


def test_equivalent_spellings_share_only_the_storage_partition_key() -> None:
    signed_spelling = "OmniNode-ai/OmniMarket"
    canonical_spelling = "omninode-ai/omnimarket"

    signed_key = canonical_repository_partition_key(signed_spelling)
    canonical_key = canonical_repository_partition_key(canonical_spelling)

    assert signed_key == canonical_key
    assert signed_spelling != canonical_spelling
    assert signed_spelling == "OmniNode-ai/OmniMarket"


def test_distinct_repositories_keep_distinct_partition_keys() -> None:
    assert canonical_repository_partition_key("OmniNode-ai/OmniMarket") != (
        canonical_repository_partition_key("OmniNode-ai/OmniBase_Core")
    )
    assert canonical_repository_partition_key("OmniNode-ai/OmniMarket") != (
        canonical_repository_partition_key("OmniNode/OmniMarket")
    )


@pytest.mark.parametrize(
    "repository",
    [
        "",
        "omnimarket",
        "/omnimarket",
        "owner/",
        "owner/repo/extra",
        "owner//repo",
        "../repo",
        "owner/..",
        "owner/../repo",
        "owner/repo/..",
        "owner/naïve",
        "ownér/repo",
        "owner/repo name",
        "-owner/repo",
        "owner/-repo",
        " owner/repo",
        "owner/repo\n",
    ],
)
def test_partition_key_rejects_values_outside_sql_repository_check(
    repository: str,
) -> None:
    with pytest.raises(ModelOnexError, match="canonical ASCII owner/repository"):
        canonical_repository_partition_key(repository)


def test_ascii_boundary_matches_market_sql_constraint_shape() -> None:
    assert SQL_REPOSITORY_CHECK_PATTERN == (
        r"^[A-Za-z0-9][A-Za-z0-9_.-]*/[A-Za-z0-9][A-Za-z0-9_.-]*$"
    )
    assert canonical_repository_partition_key("A1._-/B2._-") == "a1._-/b2._-"
