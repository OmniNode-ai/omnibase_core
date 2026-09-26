# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Fresh-completion and composition regressions for OMN-17710."""

from __future__ import annotations

import subprocess
import sys
import textwrap
from pathlib import Path
from typing import cast

import pytest
from pydantic import ValidationError

from omnibase_core.models.core.model_complex_filter import ModelComplexFilter
from omnibase_core.models.core.model_custom_filter_base import ModelCustomFilterBase
from omnibase_core.models.core.model_custom_filters import ModelCustomFilters
from omnibase_core.models.core.model_datetime_filter import ModelDateTimeFilter
from omnibase_core.models.core.model_filter_criteria import ModelFilterCriteria
from omnibase_core.models.core.model_list_filter import ModelListFilter
from omnibase_core.models.core.model_metadata_filter import ModelMetadataFilter
from omnibase_core.models.core.model_numeric_filter import ModelNumericFilter
from omnibase_core.models.core.model_status_filter import ModelStatusFilter
from omnibase_core.models.core.model_string_filter import ModelStringFilter
from omnibase_core.models.errors.model_onex_error import ModelOnexError
from omnibase_core.types.type_serializable_value import SerializedDict

pytestmark = pytest.mark.unit

_REPO_ROOT = Path(__file__).resolve().parents[4]


def _leaf_cases() -> list[tuple[type[ModelCustomFilterBase], dict[str, object]]]:
    return [
        (
            ModelStringFilter,
            {"filter_type": "string", "pattern": "error", "case_sensitive": True},
        ),
        (
            ModelNumericFilter,
            {"filter_type": "numeric", "min_value": 1.0, "max_value": 5.0},
        ),
        (
            ModelDateTimeFilter,
            {"filter_type": "datetime", "after": "2026-09-03T00:00:00Z"},
        ),
        (
            ModelListFilter,
            {"filter_type": "list", "values": ["ready", 2], "match_all": True},
        ),
        (
            ModelMetadataFilter,
            {
                "filter_type": "metadata",
                "metadata_key": "team",
                "metadata_value": "platform",
            },
        ),
        (
            ModelStatusFilter,
            {"filter_type": "status", "allowed_statuses": ["ready"]},
        ),
    ]


def _aggregate_cases() -> list[tuple[type[ModelCustomFilterBase], dict[str, object]]]:
    cases = _leaf_cases()
    cases.append(
        (
            ModelComplexFilter,
            {"filter_type": "complex", "sub_filters": [_leaf_cases()[0][1]]},
        )
    )
    return cases


def _run_fresh_python(source: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-c", textwrap.dedent(source)],
        cwd=_REPO_ROOT,
        check=False,
        capture_output=True,
        text=True,
    )


@pytest.mark.parametrize(
    "first_import",
    [
        "from omnibase_core.models.core.model_complex_filter import ModelComplexFilter",
        "from omnibase_core.models.core.model_custom_filters import ModelCustomFilters",
        "from omnibase_core.models.core.model_filter_criteria import ModelFilterCriteria",
    ],
)
def test_complex_and_aggregate_are_complete_in_fresh_import_orders(
    first_import: str,
) -> None:
    result = _run_fresh_python(
        f"""
        {first_import}
        import omnibase_core.models.core.model_custom_filter as legacy_module
        from omnibase_core.models.core.model_complex_filter import ModelComplexFilter
        from omnibase_core.models.core.model_custom_filters import ModelCustomFilters
        from omnibase_core.models.core.model_filter_criteria import ModelFilterCriteria

        assert not hasattr(legacy_module, "ModelCustomFilters")
        assert ModelComplexFilter.__pydantic_complete__ is True
        assert ModelCustomFilters.__pydantic_complete__ is True
        assert ModelComplexFilter.model_json_schema()["additionalProperties"] is False
        assert ModelCustomFilters.model_json_schema()["additionalProperties"] is False
        assert ModelFilterCriteria.model_json_schema()["title"] == "ModelFilterCriteria"
        assert ModelFilterCriteria.model_fields["custom_filters"].annotation is ModelCustomFilters
        """
    )

    assert result.returncode == 0, result.stderr


@pytest.mark.parametrize(
    ("expected_type", "leaf_payload"),
    _leaf_cases(),
    ids=[case[0].__name__ for case in _leaf_cases()],
)
def test_complex_filter_round_trips_all_six_sub_filter_variants(
    expected_type: type[ModelCustomFilterBase],
    leaf_payload: dict[str, object],
) -> None:
    complex_filter = ModelComplexFilter.model_validate(
        {"filter_type": "complex", "sub_filters": [leaf_payload]}
    )
    restored = ModelComplexFilter.model_validate_json(complex_filter.model_dump_json())

    assert restored == complex_filter
    assert type(restored.sub_filters[0]) is expected_type


@pytest.mark.parametrize(
    ("expected_type", "filter_payload"),
    _aggregate_cases(),
    ids=[case[0].__name__ for case in _aggregate_cases()],
)
def test_custom_filters_round_trip_all_seven_variants(
    expected_type: type[ModelCustomFilterBase],
    filter_payload: dict[str, object],
) -> None:
    filters = ModelCustomFilters.from_dict(
        cast(SerializedDict, {"selected": filter_payload})
    )
    restored = ModelCustomFilters.model_validate_json(filters.model_dump_json())

    assert restored == filters
    assert type(restored.filters["selected"]) is expected_type


def test_filter_criteria_uses_canonical_custom_filters_round_trip() -> None:
    criteria = ModelFilterCriteria.from_dict(
        cast(
            SerializedDict,
            {
                "logic": "OR",
                "custom_filters": {"needle": _leaf_cases()[0][1]},
            },
        )
    )

    assert criteria is not None
    assert isinstance(criteria.custom_filters.filters["needle"], ModelStringFilter)
    assert ModelFilterCriteria.from_dict(criteria.to_dict()) == criteria
    assert (
        ModelFilterCriteria.model_validate_json(criteria.model_dump_json()) == criteria
    )


@pytest.mark.parametrize(
    "payload",
    [
        {"filters": {}, "omn17710_unknown": True},
        {
            "filters": {
                "complex": {
                    "filter_type": "complex",
                    "sub_filters": [],
                    "omn17710_unknown": True,
                }
            }
        },
        {
            "filters": {
                "complex": {
                    "filter_type": "complex",
                    "sub_filters": [
                        {
                            "filter_type": "string",
                            "pattern": "error",
                            "omn17710_unknown": True,
                        }
                    ],
                }
            }
        },
    ],
)
def test_custom_filters_reject_unknown_fields_at_every_contract_boundary(
    payload: dict[str, object],
) -> None:
    with pytest.raises(ValidationError) as exc_info:
        ModelCustomFilters.model_validate(payload)

    assert any(error["type"] == "extra_forbidden" for error in exc_info.value.errors())


@pytest.mark.parametrize(
    "malformed",
    [
        {"unknown": {"filter_type": "not-a-filter"}},
        {"missing": {"pattern": "error"}},
        {"not_a_mapping": "error"},
    ],
)
def test_custom_filter_factory_rejects_unknown_or_unbound_variants(
    malformed: dict[str, object],
) -> None:
    with pytest.raises(ModelOnexError):
        ModelCustomFilters.from_dict(cast(SerializedDict, malformed))


def test_custom_filter_factory_rejects_wrong_variant_shape() -> None:
    with pytest.raises(ValidationError):
        ModelCustomFilters.from_dict(
            cast(
                SerializedDict,
                {"wrong": {"filter_type": "string", "min_value": 1.0}},
            )
        )
