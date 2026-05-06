# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""OMN-9771 normalization for miscellaneous legacy contract fields."""

import pytest

from omnibase_core.models.contracts.model_contract_base import ModelContractBase
from omnibase_core.normalization.contract_normalizer import (
    compose_normalization_pipeline,
    normalize_misc_extra_fields,
    validate_annotations_governance,
)

_KNOWN_KEYS = {
    "name",
    "node_type",
    "contract_version",
    "input_model",
    "output_model",
    "handler_routing",
    "io_operations",
    "algorithm",
    "state_machine",
    "dod_evidence",
    "yaml_consumed_events",
    "yaml_published_events",
    "published_events",
    "annotations",
    "dependencies",
    "lifecycle",
}


@pytest.mark.unit
class TestMiscExtraFieldsNormalization:
    """Migration-audit compatibility for one-off legacy annotation keys."""

    def test_unknown_keys_moved_to_annotations(self) -> None:
        raw: dict[str, object] = {
            "name": "node_foo",
            "node_type": "EFFECT_GENERIC",
            "capabilities": ["read", "write"],
            "health_check": {"endpoint": "/health"},
        }

        result = normalize_misc_extra_fields(raw, known_keys=_KNOWN_KEYS)

        assert "capabilities" not in result
        assert "health_check" not in result
        assert result["annotations"] == {
            "capabilities": ["read", "write"],
            "health_check": {"endpoint": "/health"},
        }

    def test_known_keys_not_moved(self) -> None:
        raw: dict[str, object] = {
            "name": "node_foo",
            "node_type": "EFFECT_GENERIC",
        }

        result = normalize_misc_extra_fields(raw, known_keys=_KNOWN_KEYS)

        assert result == raw

    def test_existing_annotations_are_preserved(self) -> None:
        raw: dict[str, object] = {
            "name": "node_foo",
            "annotations": {"owner": "platform"},
            "rate_limiting": {"per_minute": 60},
        }

        result = normalize_misc_extra_fields(raw, known_keys=_KNOWN_KEYS)

        assert result["annotations"] == {
            "owner": "platform",
            "rate_limiting": {"per_minute": 60},
        }

    def test_annotations_field_accepted_by_model_contract_base(self) -> None:
        assert "annotations" in ModelContractBase.model_fields

    def test_validate_annotations_governance_clean(self) -> None:
        assert (
            validate_annotations_governance(
                {"owner": "platform", "migrated_from_v0": True}
            )
            == []
        )

    def test_validate_annotations_governance_forbidden_key(self) -> None:
        violations = validate_annotations_governance({"topics": ["legacy.topic.v1"]})

        assert len(violations) == 1
        assert "topics" in violations[0]
        assert "typed field" in violations[0]

    def test_compose_pipeline_moves_misc_fields_after_legacy_strips(self) -> None:
        raw: dict[str, object] = {
            "name": "node_foo",
            "node_type": "EFFECT_GENERIC",
            "metadata": {"author": "legacy"},
            "capabilities": ["read"],
        }

        result = compose_normalization_pipeline(raw)

        assert "metadata" not in result
        assert result["annotations"] == {"capabilities": ["read"]}
