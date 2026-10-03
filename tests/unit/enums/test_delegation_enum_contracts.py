# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Pin the delegation enum wire contracts (OMN-17427)."""

from enum import StrEnum

import pytest

from omnibase_core.enums.enum_delegation_budget_refusal_reason import (
    EnumDelegationBudgetRefusalReason,
)
from omnibase_core.enums.enum_delegation_operational_outcome import (
    EnumDelegationOperationalOutcome,
)
from omnibase_core.enums.enum_delegation_output_refusal_reason import (
    EnumDelegationOutputRefusalReason,
)
from omnibase_core.enums.enum_delegation_terminal_outcome import (
    EnumDelegationTerminalOutcome,
)
from omnibase_core.enums.enum_delegation_unrouted_reason import (
    EnumDelegationUnroutedReason,
)

ENUM_CONTRACTS: tuple[tuple[type[StrEnum], tuple[tuple[str, str], ...], int], ...] = (
    (
        EnumDelegationTerminalOutcome,
        (
            ("COMPLETED", "completed"),
            ("FAILED", "failed"),
        ),
        2,
    ),
    (
        EnumDelegationBudgetRefusalReason,
        (
            (
                "TIMEOUT_EXCEEDS_TASK_CLASS_CEILING",
                "timeout_exceeds_task_class_ceiling",
            ),
        ),
        1,
    ),
    (
        EnumDelegationUnroutedReason,
        (
            ("NO_ELIGIBLE_BACKEND", "no_eligible_backend"),
            ("ROUTING_POLICY_REJECTED", "routing_policy_rejected"),
            ("ROUTING_CONFIGURATION_INVALID", "routing_configuration_invalid"),
        ),
        3,
    ),
    (
        EnumDelegationOperationalOutcome,
        (
            ("COMPLETED", "completed"),
            ("REFUSED", "refused"),
            ("SCHEMA_REJECTED", "schema_rejected"),
            ("QUALITY_REJECTED", "quality_rejected"),
            ("PROVIDER_QUOTA", "provider_quota"),
            ("PROVIDER_UNAVAILABLE", "provider_unavailable"),
            ("TIMEOUT", "timeout"),
            ("CANCELLED", "cancelled"),
            ("BOUNDARY_FAILURE", "boundary_failure"),
            ("INFERENCE_FAILED", "inference_failed"),
            ("TERMINAL_CONSTRUCTION_FAILED", "terminal_construction_failed"),
        ),
        11,
    ),
    (
        EnumDelegationOutputRefusalReason,
        (
            ("AMBIGUOUS_UNMARKED_DELIVERABLE", "ambiguous_unmarked_deliverable"),
            ("NO_SCHEMA_CONFORMING_JSON", "no_schema_conforming_json"),
        ),
        2,
    ),
)


@pytest.mark.unit
@pytest.mark.parametrize(
    ("enum_type", "expected_members"),
    [(enum_type, members) for enum_type, members, _ in ENUM_CONTRACTS],
    ids=[enum_type.__name__ for enum_type, _, _ in ENUM_CONTRACTS],
)
def test_exact_member_mapping_and_order(
    enum_type: type[StrEnum], expected_members: tuple[tuple[str, str], ...]
) -> None:
    assert (
        tuple((name, member.value) for name, member in enum_type.__members__.items())
        == expected_members
    )


@pytest.mark.unit
@pytest.mark.parametrize(
    ("enum_type", "expected_count"),
    [(enum_type, count) for enum_type, _, count in ENUM_CONTRACTS],
    ids=[enum_type.__name__ for enum_type, _, _ in ENUM_CONTRACTS],
)
def test_member_count(enum_type: type[StrEnum], expected_count: int) -> None:
    assert len(enum_type) == expected_count
    assert len(enum_type.__members__) == expected_count


@pytest.mark.unit
@pytest.mark.parametrize(
    "enum_type",
    [enum_type for enum_type, _, _ in ENUM_CONTRACTS],
    ids=[enum_type.__name__ for enum_type, _, _ in ENUM_CONTRACTS],
)
def test_string_value_round_trip(enum_type: type[StrEnum]) -> None:
    for member in enum_type:
        assert isinstance(member, str)
        assert str(member) == member.value
        assert enum_type(member.value) is member
        assert enum_type(str(member)) is member


@pytest.mark.unit
@pytest.mark.parametrize(
    "enum_type",
    [enum_type for enum_type, _, _ in ENUM_CONTRACTS],
    ids=[enum_type.__name__ for enum_type, _, _ in ENUM_CONTRACTS],
)
def test_unknown_value_is_rejected(enum_type: type[StrEnum]) -> None:
    with pytest.raises(ValueError):
        enum_type("not_a_real_delegation_value")
