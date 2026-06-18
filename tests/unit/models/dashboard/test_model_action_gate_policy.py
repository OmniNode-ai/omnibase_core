# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Unit tests for ModelActionGatePolicy (OMN-13131, ADR D2).

ModelActionGatePolicy is the canonical home in core for the UI action-gate
risk/confidence fields the rev-4 plan §6 attributes to the action contract:
``confidence_threshold``, ``requires_user_confirmation``, ``risk_level``,
``reversible``, and a commit level. The ADR
``docs/adr/2026-06-17-ui-deterministic-projection-effect-layer.md`` (D2 note)
requires these be declared in a real canonical source rather than assumed onto
``ModelGate`` — this model is that source. ``ActionContract`` (a later wave)
composes this policy; it does not fork ModelGate.

ModelGateSpec (objective scoring, OMN-2537) MUST stay untouched and distinct.
"""

import inspect

import pytest
from pydantic import ValidationError

from omnibase_core.enums.ui import EnumCommitLevel, EnumRiskLevel
from omnibase_core.models.dashboard import ModelActionGatePolicy


@pytest.mark.unit
class TestModelActionGatePolicyCanonicalLocation:
    """The model lives in the UI-platform (dashboard) models package in core."""

    def test_importable_from_dashboard_package(self) -> None:
        from omnibase_core.models.dashboard import (
            ModelActionGatePolicy as FromPackage,
        )
        from omnibase_core.models.dashboard.model_action_gate_policy import (
            ModelActionGatePolicy as FromModule,
        )

        assert FromPackage is FromModule

    def test_defined_in_core(self) -> None:
        module = ModelActionGatePolicy.__module__
        assert module.startswith("omnibase_core.")


@pytest.mark.unit
class TestModelActionGatePolicyFields:
    """The strongly-typed risk/confidence fields exist with canonical types."""

    def _valid(self) -> ModelActionGatePolicy:
        return ModelActionGatePolicy(
            confidence_threshold=0.8,
            requires_user_confirmation=True,
            risk_level=EnumRiskLevel.HIGH,
            reversible=False,
            commit_level=EnumCommitLevel.IRREVERSIBLE,
        )

    def test_all_canonical_fields_present(self) -> None:
        policy = self._valid()
        assert policy.confidence_threshold == 0.8
        assert policy.requires_user_confirmation is True
        assert policy.risk_level is EnumRiskLevel.HIGH
        assert policy.reversible is False
        assert policy.commit_level is EnumCommitLevel.IRREVERSIBLE

    def test_confidence_threshold_is_float(self) -> None:
        fields = ModelActionGatePolicy.model_fields
        assert fields["confidence_threshold"].annotation is float

    def test_risk_level_uses_enum_not_string(self) -> None:
        fields = ModelActionGatePolicy.model_fields
        assert fields["risk_level"].annotation is EnumRiskLevel

    def test_commit_level_uses_enum_not_string(self) -> None:
        fields = ModelActionGatePolicy.model_fields
        assert fields["commit_level"].annotation is EnumCommitLevel

    def test_requires_user_confirmation_is_bool(self) -> None:
        fields = ModelActionGatePolicy.model_fields
        assert fields["requires_user_confirmation"].annotation is bool

    def test_reversible_is_bool(self) -> None:
        fields = ModelActionGatePolicy.model_fields
        assert fields["reversible"].annotation is bool

    def test_confidence_threshold_rejects_below_zero(self) -> None:
        with pytest.raises(ValidationError):
            ModelActionGatePolicy(
                confidence_threshold=-0.1,
                requires_user_confirmation=False,
                risk_level=EnumRiskLevel.LOW,
                reversible=True,
                commit_level=EnumCommitLevel.READ_ONLY,
            )

    def test_confidence_threshold_rejects_above_one(self) -> None:
        with pytest.raises(ValidationError):
            ModelActionGatePolicy(
                confidence_threshold=1.5,
                requires_user_confirmation=False,
                risk_level=EnumRiskLevel.LOW,
                reversible=True,
                commit_level=EnumCommitLevel.READ_ONLY,
            )


@pytest.mark.unit
class TestModelActionGatePolicyConfig:
    """Frozen, extra-forbid value model per core Pydantic standards."""

    def test_is_frozen(self) -> None:
        policy = ModelActionGatePolicy(
            confidence_threshold=0.5,
            requires_user_confirmation=False,
            risk_level=EnumRiskLevel.LOW,
            reversible=True,
            commit_level=EnumCommitLevel.READ_ONLY,
        )
        with pytest.raises(ValidationError):
            policy.risk_level = EnumRiskLevel.HIGH  # type: ignore[misc]

    def test_extra_forbid(self) -> None:
        with pytest.raises(ValidationError):
            ModelActionGatePolicy(
                confidence_threshold=0.5,
                requires_user_confirmation=False,
                risk_level=EnumRiskLevel.LOW,
                reversible=True,
                commit_level=EnumCommitLevel.READ_ONLY,
                bogus="x",  # type: ignore[call-arg]
            )


@pytest.mark.unit
class TestModelGateSpecUntouched:
    """ADR D2: ModelGateSpec (objective scoring) must NOT be merged/changed."""

    def test_gate_spec_still_objective_scoring(self) -> None:
        from omnibase_core.models.objective.model_gate_spec import ModelGateSpec

        fields = set(ModelGateSpec.model_fields)
        assert fields == {"id", "type", "threshold", "weight"}

    def test_gate_spec_has_no_risk_fields(self) -> None:
        from omnibase_core.models.objective.model_gate_spec import ModelGateSpec

        fields = set(ModelGateSpec.model_fields)
        assert "risk_level" not in fields
        assert "confidence_threshold" not in fields
        assert "commit_level" not in fields

    def test_gate_spec_source_unchanged_signature(self) -> None:
        """ModelGateSpec is a distinct concept; it does not compose the policy."""
        from omnibase_core.models.objective.model_gate_spec import ModelGateSpec

        src = inspect.getsource(ModelGateSpec)
        assert "ModelActionGatePolicy" not in src


@pytest.mark.unit
class TestModelActionContractComposesPolicy:
    """ADR D2: ModelActionContract composes the risk policy (not ModelGate)."""

    def test_action_contract_has_gate_policy_field(self) -> None:
        from omnibase_core.models.dashboard import ModelActionContract

        assert "gate_policy" in ModelActionContract.model_fields

    def test_gate_policy_field_typed_as_policy_or_none(self) -> None:
        from omnibase_core.models.dashboard import ModelActionContract

        annotation = ModelActionContract.model_fields["gate_policy"].annotation
        assert annotation == (ModelActionGatePolicy | None)

    def test_action_contract_consumes_policy(self) -> None:
        from omnibase_core.models.dashboard import ModelActionContract

        policy = ModelActionGatePolicy(
            confidence_threshold=0.9,
            requires_user_confirmation=True,
            risk_level=EnumRiskLevel.CRITICAL,
            reversible=False,
            commit_level=EnumCommitLevel.IRREVERSIBLE,
        )
        contract = ModelActionContract(
            action_id="delegate.trigger",
            command_topic="onex.cmd.delegation.trigger.v1",
            label="Delegate",
            gate_policy=policy,
        )
        assert contract.gate_policy is policy
        assert contract.gate_policy.risk_level is EnumRiskLevel.CRITICAL

    def test_gate_policy_defaults_to_none(self) -> None:
        from omnibase_core.models.dashboard import ModelActionContract

        contract = ModelActionContract(
            action_id="refresh.view",
            command_topic="onex.cmd.dashboard.refresh.v1",
            label="Refresh",
        )
        assert contract.gate_policy is None

    def test_action_contract_does_not_put_risk_fields_on_gate(self) -> None:
        """The risk fields live on the policy, never on the approval gate."""
        from omnibase_core.models.ticket.model_gate import ModelGate

        gate_fields = set(ModelGate.model_fields)
        assert "risk_level" not in gate_fields
        assert "confidence_threshold" not in gate_fields
        assert "commit_level" not in gate_fields
        assert "reversible" not in gate_fields
