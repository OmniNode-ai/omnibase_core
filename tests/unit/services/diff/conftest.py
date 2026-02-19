# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""
Shared fixtures for diff storage service tests.

Provides reusable test fixtures for ModelContractDiff instances and
related test data.

OMN-1149: TDD tests for diff storage infrastructure.

.. versionadded:: 0.6.0
    Added as part of Diff Storage Infrastructure (OMN-1149)
"""

from datetime import UTC, datetime, timedelta

import pytest

from omnibase_core.enums.enum_contract_diff_change_type import (
    EnumContractDiffChangeType,
)
from omnibase_core.models.common.model_schema_value import ModelSchemaValue
from omnibase_core.models.contracts.diff import (
    ModelContractDiff,
    ModelContractFieldDiff,
)

# ============================================================================
# Helper Functions
# ============================================================================


def create_test_diff(
    *,
    before_contract_name: str = "ContractA",
    after_contract_name: str = "ContractA",
    computed_at: datetime | None = None,
    diff_id: None = None,
    with_changes: bool = True,
) -> ModelContractDiff:
    """
    Create a test diff with specified parameters.

    Args:
        before_contract_name: Name of the before contract.
        after_contract_name: Name of the after contract.
        computed_at: Timestamp when diff was computed (defaults to now).
        diff_id: Optional diff ID (auto-generated if not provided).
        with_changes: Whether to include field diffs (defaults to True).

    Returns:
        A ModelContractDiff instance for testing.
    """
    field_diffs: list[ModelContractFieldDiff] = []

    if with_changes:
        field_diffs = [
            ModelContractFieldDiff(
                field_path="meta.name",
                change_type=EnumContractDiffChangeType.MODIFIED,
                old_value=ModelSchemaValue.from_value("Old"),
                new_value=ModelSchemaValue.from_value("New"),
                value_type="str",
            ),
        ]

    kwargs: dict = {
        "before_contract_name": before_contract_name,
        "after_contract_name": after_contract_name,
        "field_diffs": field_diffs,
        "list_diffs": [],
    }

    if computed_at is not None:
        kwargs["computed_at"] = computed_at

    if diff_id is not None:
        kwargs["diff_id"] = diff_id

    return ModelContractDiff(**kwargs)


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def sample_diff() -> ModelContractDiff:
    """Create a sample diff with one field change."""
    return create_test_diff()


@pytest.fixture
def sample_diff_no_changes() -> ModelContractDiff:
    """Create a sample diff with no changes."""
    return create_test_diff(with_changes=False)


@pytest.fixture
def sample_diffs() -> list[ModelContractDiff]:
    """Create multiple diffs for query testing."""
    now = datetime.now(UTC)
    return [
        create_test_diff(
            computed_at=now - timedelta(hours=i),
        )
        for i in range(5)
    ]


@pytest.fixture
def sample_diffs_multiple_contracts() -> list[ModelContractDiff]:
    """Create diffs for multiple different contracts."""
    now = datetime.now(UTC)
    return [
        create_test_diff(
            before_contract_name="ContractA",
            after_contract_name="ContractA",
            computed_at=now - timedelta(hours=0),
        ),
        create_test_diff(
            before_contract_name="ContractA",
            after_contract_name="ContractA",
            computed_at=now - timedelta(hours=1),
        ),
        create_test_diff(
            before_contract_name="ContractB",
            after_contract_name="ContractB",
            computed_at=now - timedelta(hours=2),
        ),
        create_test_diff(
            before_contract_name="ContractC",
            after_contract_name="ContractC",
            computed_at=now - timedelta(hours=3),
        ),
    ]


@pytest.fixture
def field_diff_added() -> ModelContractFieldDiff:
    """Create an ADDED field diff."""
    return ModelContractFieldDiff(
        field_path="new_field",
        change_type=EnumContractDiffChangeType.ADDED,
        old_value=None,
        new_value=ModelSchemaValue.from_value("added_value"),
        value_type="str",
    )


@pytest.fixture
def field_diff_removed() -> ModelContractFieldDiff:
    """Create a REMOVED field diff."""
    return ModelContractFieldDiff(
        field_path="old_field",
        change_type=EnumContractDiffChangeType.REMOVED,
        old_value=ModelSchemaValue.from_value("removed_value"),
        new_value=None,
        value_type="str",
    )


@pytest.fixture
def field_diff_modified() -> ModelContractFieldDiff:
    """Create a MODIFIED field diff."""
    return ModelContractFieldDiff(
        field_path="changed_field",
        change_type=EnumContractDiffChangeType.MODIFIED,
        old_value=ModelSchemaValue.from_value("old_value"),
        new_value=ModelSchemaValue.from_value("new_value"),
        value_type="str",
    )
