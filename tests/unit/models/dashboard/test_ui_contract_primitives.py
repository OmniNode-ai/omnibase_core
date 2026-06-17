# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Unit tests for the Phase 0 UI contract primitives (OMN-13130).

Covers the six frozen Pydantic primitives plus ``EnumEmptyStateReason``:
frozen immutability, ``extra="forbid"``, required fields, strong typing, and
composition of the existing ``ModelGate`` / ``ModelEvidenceRequirement``
primitives (not duplication).
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from omnibase_core.enums import (
    EnumAccessibilityTier,
    EnumEmptyStateReason,
    EnumEvidenceGateMoment,
    EnumRendererInteractionModel,
    EnumWidgetType,
)
from omnibase_core.enums.ticket import EnumGateKind
from omnibase_core.enums.ticket.enum_evidence_kind import EnumEvidenceKind
from omnibase_core.models.dashboard import (
    EnumBindingOrderDirection,
    ModelActionContract,
    ModelComponentContract,
    ModelDataBindingContract,
    ModelEvidenceRequirementContract,
    ModelPermissionContract,
    ModelRendererCapabilityContract,
)
from omnibase_core.models.primitives.model_semver import ModelSemVer
from omnibase_core.models.ticket.model_evidence_requirement import (
    ModelEvidenceRequirement,
)
from omnibase_core.models.ticket.model_gate import ModelGate


@pytest.mark.unit
class TestEnumEmptyStateReason:
    """The empty-state reason vocabulary must match chart-config.ts exactly."""

    def test_exactly_four_values(self) -> None:
        assert {member.value for member in EnumEmptyStateReason} == {
            "no-data",
            "missing-field",
            "upstream-blocked",
            "schema-invalid",
        }

    def test_value_identities(self) -> None:
        assert EnumEmptyStateReason.NO_DATA.value == "no-data"
        assert EnumEmptyStateReason.MISSING_FIELD.value == "missing-field"
        assert EnumEmptyStateReason.UPSTREAM_BLOCKED.value == "upstream-blocked"
        assert EnumEmptyStateReason.SCHEMA_INVALID.value == "schema-invalid"

    def test_is_str_enum(self) -> None:
        assert EnumEmptyStateReason.NO_DATA == "no-data"


@pytest.mark.unit
class TestModelDataBindingContract:
    """DataBindingContract: projection bind + explicit ordering authority."""

    def _make(self) -> ModelDataBindingContract:
        return ModelDataBindingContract(
            binding_id="rows",
            projection_topic="onex.evt.omnimarket.node-generation-completed.v1",
            ordering_authority_field="created_at",
            required_fields=("id", "status"),
        )

    def test_minimal_creation_and_defaults(self) -> None:
        binding = self._make()
        assert binding.ordering_direction == EnumBindingOrderDirection.DESCENDING
        assert binding.cursor_field is None
        assert binding.required_fields == ("id", "status")

    def test_frozen(self) -> None:
        binding = self._make()
        with pytest.raises(ValidationError):
            binding.projection_topic = "other"  # type: ignore[misc]

    def test_extra_forbidden(self) -> None:
        with pytest.raises(ValidationError):
            ModelDataBindingContract(
                binding_id="rows",
                projection_topic="t",
                ordering_authority_field="created_at",
                unknown="x",  # type: ignore[call-arg]
            )

    def test_required_fields_present(self) -> None:
        with pytest.raises(ValidationError):
            ModelDataBindingContract(binding_id="rows")  # type: ignore[call-arg]

    def test_ordering_direction_is_typed_enum(self) -> None:
        binding = ModelDataBindingContract(
            binding_id="rows",
            projection_topic="t",
            ordering_authority_field="created_at",
            ordering_direction=EnumBindingOrderDirection.ASCENDING,
        )
        assert binding.ordering_direction is EnumBindingOrderDirection.ASCENDING

    def test_empty_required_string_rejected(self) -> None:
        with pytest.raises(ValidationError):
            ModelDataBindingContract(
                binding_id="",
                projection_topic="t",
                ordering_authority_field="created_at",
            )


@pytest.mark.unit
class TestModelPermissionContract:
    """PermissionContract: scopes + mandatory disabled reason."""

    def _make(self) -> ModelPermissionContract:
        return ModelPermissionContract(
            permission_id="admin-only",
            act_scopes=("dashboard:write",),
            disabled_reason="Requires dashboard:write scope",
        )

    def test_minimal_creation_and_defaults(self) -> None:
        perm = self._make()
        assert perm.view_scopes == ()
        assert perm.act_scopes == ("dashboard:write",)

    def test_frozen(self) -> None:
        perm = self._make()
        with pytest.raises(ValidationError):
            perm.disabled_reason = "x"  # type: ignore[misc]

    def test_extra_forbidden(self) -> None:
        with pytest.raises(ValidationError):
            ModelPermissionContract(
                permission_id="p",
                disabled_reason="r",
                unknown="x",  # type: ignore[call-arg]
            )

    def test_disabled_reason_required(self) -> None:
        with pytest.raises(ValidationError):
            ModelPermissionContract(permission_id="p")  # type: ignore[call-arg]

    def test_disabled_reason_non_empty(self) -> None:
        with pytest.raises(ValidationError):
            ModelPermissionContract(permission_id="p", disabled_reason="")


@pytest.mark.unit
class TestModelEvidenceRequirementContract:
    """EvidenceRequirementContract composes the OCC evidence requirement."""

    def _make(self) -> ModelEvidenceRequirementContract:
        return ModelEvidenceRequirementContract(
            contract_id="needs-tests",
            requirement=ModelEvidenceRequirement(
                kind=EnumEvidenceKind.TESTS,
                description="unit tests pass",
            ),
            gate_moment=EnumEvidenceGateMoment.ON_COMMIT,
            unmet_display_message="Run the test suite before committing",
        )

    def test_composes_evidence_requirement(self) -> None:
        contract = self._make()
        assert isinstance(contract.requirement, ModelEvidenceRequirement)
        assert contract.requirement.kind is EnumEvidenceKind.TESTS
        assert contract.gate_moment is EnumEvidenceGateMoment.ON_COMMIT

    def test_frozen(self) -> None:
        contract = self._make()
        with pytest.raises(ValidationError):
            contract.unmet_display_message = "x"  # type: ignore[misc]

    def test_extra_forbidden(self) -> None:
        with pytest.raises(ValidationError):
            ModelEvidenceRequirementContract(
                contract_id="c",
                requirement=ModelEvidenceRequirement(
                    kind=EnumEvidenceKind.TESTS, description="d"
                ),
                gate_moment=EnumEvidenceGateMoment.ON_RENDER,
                unmet_display_message="m",
                unknown="x",  # type: ignore[call-arg]
            )

    def test_required_fields_present(self) -> None:
        with pytest.raises(ValidationError):
            ModelEvidenceRequirementContract(contract_id="c")  # type: ignore[call-arg]


@pytest.mark.unit
class TestModelActionContract:
    """ActionContract composes ModelGate and constrains command topics."""

    def _make(self, gate: ModelGate | None = None) -> ModelActionContract:
        return ModelActionContract(
            action_id="trigger-delegation",
            command_topic="onex.cmd.omnimarket.delegate-skill.v1",
            label="Delegate",
            approval_gate=gate,
        )

    def test_minimal_creation_and_defaults(self) -> None:
        action = self._make()
        assert action.approval_gate is None
        assert action.correlation_required is True

    def test_composes_model_gate_not_duplicates(self) -> None:
        gate = ModelGate(
            id="approve-delegation",
            kind=EnumGateKind.HUMAN_APPROVAL,
            description="Operator must approve the delegation",
        )
        action = self._make(gate=gate)
        assert isinstance(action.approval_gate, ModelGate)
        assert action.approval_gate.id == "approve-delegation"

    def test_command_topic_must_be_canonical_command(self) -> None:
        with pytest.raises(ValidationError):
            ModelActionContract(
                action_id="a",
                command_topic="onex.evt.something.v1",
                label="x",
            )

    def test_frozen(self) -> None:
        action = self._make()
        with pytest.raises(ValidationError):
            action.label = "x"  # type: ignore[misc]

    def test_extra_forbidden(self) -> None:
        with pytest.raises(ValidationError):
            ModelActionContract(
                action_id="a",
                command_topic="onex.cmd.x.y.v1",
                label="x",
                unknown="x",  # type: ignore[call-arg]
            )

    def test_required_fields_present(self) -> None:
        with pytest.raises(ValidationError):
            ModelActionContract(action_id="a")  # type: ignore[call-arg]


@pytest.mark.unit
class TestModelRendererCapabilityContract:
    """RendererCapabilityContract: advertised capability surface (model only)."""

    def _make(self) -> ModelRendererCapabilityContract:
        return ModelRendererCapabilityContract(
            renderer_id="ui.effect.web",
            platform="web",
            supported_component_kinds=(EnumWidgetType.CHART, EnumWidgetType.TABLE),
            interaction_model=EnumRendererInteractionModel.POINTER,
            accessibility_tier=EnumAccessibilityTier.AA,
            contract_version=ModelSemVer(major=1, minor=0, patch=0),
            supports_interaction=True,
        )

    def test_minimal_creation_and_defaults(self) -> None:
        cap = self._make()
        assert cap.supports_streaming is False
        assert cap.supports_theming is False
        assert cap.supports_interaction is True

    def test_strong_typing_component_kinds(self) -> None:
        cap = self._make()
        assert cap.supported_component_kinds[0] is EnumWidgetType.CHART
        assert cap.interaction_model is EnumRendererInteractionModel.POINTER
        assert cap.accessibility_tier is EnumAccessibilityTier.AA

    def test_frozen(self) -> None:
        cap = self._make()
        with pytest.raises(ValidationError):
            cap.platform = "ios"  # type: ignore[misc]

    def test_extra_forbidden(self) -> None:
        with pytest.raises(ValidationError):
            ModelRendererCapabilityContract(
                renderer_id="r",
                platform="web",
                supported_component_kinds=(EnumWidgetType.CHART,),
                interaction_model=EnumRendererInteractionModel.POINTER,
                accessibility_tier=EnumAccessibilityTier.A,
                contract_version=ModelSemVer(major=1, minor=0, patch=0),
                unknown="x",  # type: ignore[call-arg]
            )

    def test_required_fields_present(self) -> None:
        with pytest.raises(ValidationError):
            ModelRendererCapabilityContract(renderer_id="r")  # type: ignore[call-arg]

    def test_invalid_component_kind_rejected(self) -> None:
        with pytest.raises(ValidationError):
            ModelRendererCapabilityContract(
                renderer_id="r",
                platform="web",
                supported_component_kinds=("not-a-kind",),  # type: ignore[arg-type]
                interaction_model=EnumRendererInteractionModel.POINTER,
                accessibility_tier=EnumAccessibilityTier.A,
                contract_version=ModelSemVer(major=1, minor=0, patch=0),
            )


@pytest.mark.unit
class TestModelComponentContract:
    """ComponentContract composes the other Phase 0 primitives."""

    def _make(self) -> ModelComponentContract:
        return ModelComponentContract(
            component_id="generation-feed",
            component_kind=EnumWidgetType.EVENT_FEED,
            title="Generation Feed",
            contract_version=ModelSemVer(major=1, minor=0, patch=0),
            data_bindings=(
                ModelDataBindingContract(
                    binding_id="rows",
                    projection_topic="onex.evt.omnimarket.node-generation-completed.v1",
                    ordering_authority_field="created_at",
                ),
            ),
            actions=(
                ModelActionContract(
                    action_id="trigger",
                    command_topic="onex.cmd.omnimarket.delegate-skill.v1",
                    label="Delegate",
                ),
            ),
            supported_empty_state_reasons=(
                EnumEmptyStateReason.NO_DATA,
                EnumEmptyStateReason.UPSTREAM_BLOCKED,
            ),
        )

    def test_minimal_creation_and_defaults(self) -> None:
        comp = ModelComponentContract(
            component_id="c",
            component_kind=EnumWidgetType.CHART,
            title="Chart",
            contract_version=ModelSemVer(major=1, minor=0, patch=0),
        )
        assert comp.data_bindings == ()
        assert comp.actions == ()
        assert comp.evidence_requirements == ()
        assert comp.permission is None
        assert comp.supported_empty_state_reasons == ()

    def test_composes_primitives(self) -> None:
        comp = self._make()
        assert isinstance(comp.data_bindings[0], ModelDataBindingContract)
        assert isinstance(comp.actions[0], ModelActionContract)
        assert comp.component_kind is EnumWidgetType.EVENT_FEED
        assert (
            EnumEmptyStateReason.UPSTREAM_BLOCKED in comp.supported_empty_state_reasons
        )

    def test_frozen(self) -> None:
        comp = self._make()
        with pytest.raises(ValidationError):
            comp.title = "x"  # type: ignore[misc]

    def test_extra_forbidden(self) -> None:
        with pytest.raises(ValidationError):
            ModelComponentContract(
                component_id="c",
                component_kind=EnumWidgetType.CHART,
                title="x",
                contract_version=ModelSemVer(major=1, minor=0, patch=0),
                unknown="x",  # type: ignore[call-arg]
            )

    def test_required_fields_present(self) -> None:
        with pytest.raises(ValidationError):
            ModelComponentContract(component_id="c")  # type: ignore[call-arg]

    def test_json_roundtrip(self) -> None:
        comp = self._make()
        restored = ModelComponentContract.model_validate_json(comp.model_dump_json())
        assert restored == comp
