# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Tests for OMN-11221 architectural invariant extensions."""

from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from omnibase_core.enums.enum_enforcement_surface import EnumEnforcementSurface
from omnibase_core.enums.enum_invariant_type import EnumInvariantType
from omnibase_core.enums.enum_violation_category import EnumViolationCategory
from omnibase_core.models.invariant import ModelInvariant
from omnibase_core.models.invariant.model_invariant_waiver import ModelInvariantWaiver


@pytest.mark.unit
class TestEnumEnforcementSurface:
    def test_all_values_present(self) -> None:
        values = {s.value for s in EnumEnforcementSurface}
        assert values == {
            "static_architecture",
            "ci_gate",
            "pre_tool_use",
            "runtime_validation",
            "contract_validation",
        }

    def test_str_returns_value(self) -> None:
        assert str(EnumEnforcementSurface.CI_GATE) == "ci_gate"


@pytest.mark.unit
class TestEnumViolationCategory:
    def test_all_values_present(self) -> None:
        values = {c.value for c in EnumViolationCategory}
        assert values == {
            "static_architecture",
            "runtime_topology",
            "contract_violation",
            "projection_authority",
            "receipt_governance",
        }

    def test_str_returns_value(self) -> None:
        assert str(EnumViolationCategory.CONTRACT_VIOLATION) == "contract_violation"


@pytest.mark.unit
class TestModelInvariantExtensions:
    def _base_invariant(self) -> ModelInvariant:
        return ModelInvariant(
            name="test-invariant",
            type=EnumInvariantType.CUSTOM,
            config={"callable_path": "my.module.check"},
        )

    def test_new_fields_have_defaults(self) -> None:
        inv = self._base_invariant()
        assert inv.enforcement_surfaces == []
        assert inv.violation_examples == []
        assert inv.runtime_scope is None
        assert inv.generated_from_principle is None
        assert inv.generated_at is None
        assert inv.source_incidents == []
        assert inv.generator_tag is None

    def test_enforcement_surfaces_populated(self) -> None:
        inv = ModelInvariant(
            name="test",
            type=EnumInvariantType.CUSTOM,
            config={"callable_path": "my.module.check"},
            enforcement_surfaces=[
                EnumEnforcementSurface.CI_GATE,
                EnumEnforcementSurface.STATIC_ARCHITECTURE,
            ],
        )
        assert EnumEnforcementSurface.CI_GATE in inv.enforcement_surfaces
        assert len(inv.enforcement_surfaces) == 2

    def test_generated_from_principle_set(self) -> None:
        inv = ModelInvariant(
            name="test",
            type=EnumInvariantType.CUSTOM,
            config={"callable_path": "my.module.check"},
            generated_from_principle="ARCH-001",
            generated_at=datetime(2026, 5, 18, tzinfo=UTC),
            generator_tag="1.0.0",
        )
        assert inv.generated_from_principle == "ARCH-001"
        assert inv.generator_tag == "1.0.0"

    def test_source_incidents_populated(self) -> None:
        inv = ModelInvariant(
            name="test",
            type=EnumInvariantType.CUSTOM,
            config={"callable_path": "my.module.check"},
            source_incidents=["OMN-6925", "OMN-7093"],
        )
        assert "OMN-6925" in inv.source_incidents

    def test_frozen_model_immutable(self) -> None:
        inv = self._base_invariant()
        with pytest.raises((ValidationError, TypeError)):
            inv.runtime_scope = "node"  # type: ignore[misc]


@pytest.mark.unit
class TestModelInvariantWaiver:
    def _valid_waiver(self) -> ModelInvariantWaiver:
        return ModelInvariantWaiver(
            approved_exception_receipt="approval-2026-001",
            principle_code="ARCH-001",
            expires_at=datetime(2026, 12, 31, tzinfo=UTC),
            reviewer="jonah@omninode.ai",
            justification="Legacy migration window — tracked in OMN-9999",
        )

    def test_valid_waiver_creation(self) -> None:
        w = self._valid_waiver()
        assert w.approved_exception_receipt == "approval-2026-001"
        assert w.principle_code == "ARCH-001"
        assert w.reviewer == "jonah@omninode.ai"

    def test_waiver_requires_all_fields(self) -> None:
        with pytest.raises(ValidationError):
            ModelInvariantWaiver(  # type: ignore[call-arg]
                approved_exception_receipt="x",
                principle_code="ARCH-001",
                expires_at=datetime(2026, 12, 31, tzinfo=UTC),
                reviewer="user",
                # missing justification
            )

    def test_waiver_frozen(self) -> None:
        w = self._valid_waiver()
        with pytest.raises((ValidationError, TypeError)):
            w.reviewer = "other"  # type: ignore[misc]
