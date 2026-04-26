# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Unit tests for EnumContractBucket (OMN-9758, parent OMN-9757).

Validates the corpus-classification bucket enum used by the corpus
classification + normalization layer.
"""

import json

import pytest
import yaml
from pydantic import BaseModel, ValidationError

from omnibase_core.enums.enum_contract_bucket import EnumContractBucket


@pytest.mark.unit
class TestEnumContractBucketStructure:
    """Test basic enum structure and values from the corpus plan spec."""

    def test_all_expected_buckets_present(self) -> None:
        expected = {
            "node_root_contract",
            "handler_contract",
            "package_contract",
            "integration_contract",
            "service_contract",
            "fixture_or_test",
            "unknown",
        }
        actual = {b.value for b in EnumContractBucket}
        assert actual == expected

    def test_bucket_is_str_enum(self) -> None:
        assert isinstance(EnumContractBucket.NODE_ROOT_CONTRACT, str)

    def test_member_count_is_seven(self) -> None:
        assert len(list(EnumContractBucket)) == 7

    def test_enum_is_unique(self) -> None:
        values = [m.value for m in EnumContractBucket]
        assert len(values) == len(set(values))

    def test_enum_from_value(self) -> None:
        assert (
            EnumContractBucket("node_root_contract")
            is EnumContractBucket.NODE_ROOT_CONTRACT
        )

    def test_invalid_value_raises(self) -> None:
        with pytest.raises(ValueError):
            EnumContractBucket("not_a_real_bucket")

    def test_enum_equality_with_string(self) -> None:
        assert EnumContractBucket.HANDLER_CONTRACT == "handler_contract"


@pytest.mark.unit
class TestEnumContractBucketSerialization:
    """Test JSON / YAML / Pydantic round-trip safety."""

    def test_json_serialization_via_value(self) -> None:
        data = {"bucket": EnumContractBucket.NODE_ROOT_CONTRACT.value}
        assert json.dumps(data) == '{"bucket": "node_root_contract"}'

    def test_yaml_round_trip(self) -> None:
        data = {"bucket": EnumContractBucket.HANDLER_CONTRACT.value}
        loaded = yaml.safe_load(yaml.dump(data))
        assert loaded["bucket"] == "handler_contract"
        assert (
            EnumContractBucket(loaded["bucket"]) is EnumContractBucket.HANDLER_CONTRACT
        )

    def test_pydantic_field_assignment(self) -> None:
        class M(BaseModel):
            bucket: EnumContractBucket

        m = M(bucket=EnumContractBucket.PACKAGE_CONTRACT)
        assert m.bucket is EnumContractBucket.PACKAGE_CONTRACT

    def test_pydantic_string_coercion(self) -> None:
        class M(BaseModel):
            bucket: EnumContractBucket

        m = M(bucket="integration_contract")
        assert m.bucket is EnumContractBucket.INTEGRATION_CONTRACT

    def test_pydantic_invalid_raises(self) -> None:
        class M(BaseModel):
            bucket: EnumContractBucket

        with pytest.raises(ValidationError):
            M(bucket="bogus_bucket")

    def test_pydantic_model_dump(self) -> None:
        class M(BaseModel):
            bucket: EnumContractBucket

        m = M(bucket=EnumContractBucket.SERVICE_CONTRACT)
        assert m.model_dump() == {"bucket": "service_contract"}

    def test_pydantic_model_dump_json(self) -> None:
        class M(BaseModel):
            bucket: EnumContractBucket

        m = M(bucket=EnumContractBucket.FIXTURE_OR_TEST)
        assert m.model_dump_json() == '{"bucket":"fixture_or_test"}'


@pytest.mark.unit
class TestEnumContractBucketExports:
    """Verify the enum is re-exported from the enums package __init__."""

    def test_exported_from_enums_init(self) -> None:
        from omnibase_core import enums as enums_pkg

        assert hasattr(enums_pkg, "EnumContractBucket")
        assert enums_pkg.EnumContractBucket is EnumContractBucket
