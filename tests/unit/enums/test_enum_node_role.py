# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""
Unit tests for EnumNodeRole.

Covers:
- Enum value existence and correctness (all 9 values)
- String conversion and comparison
- Serialization/deserialization
- Pydantic model compatibility (including ModelOnexMetadata.node_role)
- Backward compatibility: existing metadata without node_role parses without error
"""

import json

import pytest

from omnibase_core.enums.enum_node_role import EnumNodeRole


@pytest.mark.unit
class TestEnumNodeRoleValues:
    """Verify all 9 required enum values exist with correct string representations."""

    def test_all_nine_values_exist(self) -> None:
        expected_names = {
            "INVENTORY",
            "TRIAGE",
            "FIX",
            "PROBE",
            "REPORT",
            "ORCHESTRATOR",
            "REDUCER",
            "EFFECT",
            "INTERNAL",
        }
        actual_names = {member.name for member in EnumNodeRole}
        assert actual_names == expected_names

    def test_enum_member_count(self) -> None:
        assert len(list(EnumNodeRole)) == 9

    def test_string_values(self) -> None:
        expected = {
            EnumNodeRole.INVENTORY: "inventory",
            EnumNodeRole.TRIAGE: "triage",
            EnumNodeRole.FIX: "fix",
            EnumNodeRole.PROBE: "probe",
            EnumNodeRole.REPORT: "report",
            EnumNodeRole.ORCHESTRATOR: "orchestrator",
            EnumNodeRole.REDUCER: "reducer",
            EnumNodeRole.EFFECT: "effect",
            EnumNodeRole.INTERNAL: "internal",
        }
        for member, expected_value in expected.items():
            assert member.value == expected_value
            assert str(member) == expected_value

    def test_values_are_unique(self) -> None:
        values = [m.value for m in EnumNodeRole]
        assert len(values) == len(set(values))


@pytest.mark.unit
class TestEnumNodeRoleInheritance:
    """Verify enum inherits from str and Enum correctly."""

    def test_inherits_from_str(self) -> None:
        from enum import Enum

        assert issubclass(EnumNodeRole, str)
        assert issubclass(EnumNodeRole, Enum)

    def test_members_are_strings(self) -> None:
        for member in list(EnumNodeRole):
            assert isinstance(member, str)

    def test_string_equality(self) -> None:
        assert EnumNodeRole.INVENTORY == "inventory"
        assert EnumNodeRole.TRIAGE == "triage"
        assert EnumNodeRole.FIX == "fix"
        assert EnumNodeRole.PROBE == "probe"
        assert EnumNodeRole.REPORT == "report"
        assert EnumNodeRole.ORCHESTRATOR == "orchestrator"
        assert EnumNodeRole.REDUCER == "reducer"
        assert EnumNodeRole.EFFECT == "effect"
        assert EnumNodeRole.INTERNAL == "internal"


@pytest.mark.unit
class TestEnumNodeRoleSerialization:
    """Verify round-trip serialization."""

    def test_construct_from_string(self) -> None:
        for member in list(EnumNodeRole):
            reconstructed = EnumNodeRole(member.value)
            assert reconstructed is member

    def test_json_roundtrip(self) -> None:
        for member in list(EnumNodeRole):
            serialized = json.dumps(member.value)
            deserialized = json.loads(serialized)
            assert EnumNodeRole(deserialized) is member

    def test_invalid_value_raises(self) -> None:
        with pytest.raises(ValueError):
            EnumNodeRole("nonexistent_role")

    def test_case_sensitive(self) -> None:
        with pytest.raises(ValueError):
            EnumNodeRole("INVENTORY")

        with pytest.raises(ValueError):
            EnumNodeRole("Inventory")


@pytest.mark.unit
class TestEnumNodeRolePydanticCompatibility:
    """Verify enum works with Pydantic models."""

    def test_pydantic_field(self) -> None:
        from pydantic import BaseModel

        class M(BaseModel):
            role: EnumNodeRole

        m = M(role=EnumNodeRole.TRIAGE)
        assert m.role == EnumNodeRole.TRIAGE

        m2 = M(role="fix")
        assert m2.role == EnumNodeRole.FIX

        data = m2.model_dump()
        assert data["role"] == "fix"

        m3 = M.model_validate(data)
        assert m3.role == EnumNodeRole.FIX

    def test_optional_pydantic_field(self) -> None:
        from pydantic import BaseModel

        class M(BaseModel):
            role: EnumNodeRole | None = None

        m_none = M()
        assert m_none.role is None

        m_set = M(role="probe")
        assert m_set.role == EnumNodeRole.PROBE


@pytest.mark.unit
class TestModelMetadataBlockNodeRole:
    """Verify ModelMetadataBlock accepts node_role and is backward compatible.

    Uses ModelMetadataBlock (fully resolved imports) rather than ModelOnexMetadata
    (which uses TYPE_CHECKING forward refs requiring model_rebuild).
    """

    def _base_metadata_kwargs(self) -> dict:
        from omnibase_core.enums import EnumProtocolVersion

        return {
            "name": "test_node",
            "namespace": "omninode.test",
            "protocols_supported": ["onex/v1"],
            "protocol_version": EnumProtocolVersion.V1_0_0,
            "author": "Test Author",
            "owner": "omninode",
            "copyright": "2025 OmniNode.ai Inc.",
            "created_at": "2025-01-01T00:00:00Z",
            "last_modified_at": "2025-01-01T00:00:00Z",
        }

    def test_node_role_defaults_to_none(self) -> None:
        from omnibase_core.models.configuration.model_metadata_block import (
            ModelMetadataBlock,
        )

        m = ModelMetadataBlock(**self._base_metadata_kwargs())
        assert m.node_role is None

    def test_node_role_accepts_enum_value(self) -> None:
        from omnibase_core.models.configuration.model_metadata_block import (
            ModelMetadataBlock,
        )

        kwargs = self._base_metadata_kwargs()
        kwargs["node_role"] = EnumNodeRole.INVENTORY
        m = ModelMetadataBlock(**kwargs)
        assert m.node_role == EnumNodeRole.INVENTORY

    def test_node_role_accepts_string_value(self) -> None:
        from omnibase_core.models.configuration.model_metadata_block import (
            ModelMetadataBlock,
        )

        kwargs = self._base_metadata_kwargs()
        kwargs["node_role"] = "triage"
        m = ModelMetadataBlock(**kwargs)
        assert m.node_role == EnumNodeRole.TRIAGE

    def test_node_role_all_values_accepted(self) -> None:
        from omnibase_core.models.configuration.model_metadata_block import (
            ModelMetadataBlock,
        )

        for role in list(EnumNodeRole):
            kwargs = self._base_metadata_kwargs()
            kwargs["node_role"] = role
            m = ModelMetadataBlock(**kwargs)
            assert m.node_role == role

    def test_existing_metadata_without_node_role_parses(self) -> None:
        """Backward compat: metadata without node_role must parse without error."""
        from omnibase_core.models.configuration.model_metadata_block import (
            ModelMetadataBlock,
        )

        m = ModelMetadataBlock(**self._base_metadata_kwargs())
        assert m.node_role is None

    def test_node_role_serializes_correctly(self) -> None:
        from omnibase_core.models.configuration.model_metadata_block import (
            ModelMetadataBlock,
        )

        kwargs = self._base_metadata_kwargs()
        kwargs["node_role"] = EnumNodeRole.REPORT
        m = ModelMetadataBlock(**kwargs)
        data = m.model_dump()
        assert data["node_role"] == "report"
