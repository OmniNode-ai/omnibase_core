# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Tests for session contract unification (OMN-11225)."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

pytestmark = pytest.mark.unit


@pytest.mark.unit
class TestSessionPhaseSpecUnification:
    """ModelSessionPhaseSpec must carry required_outcomes and halt_conditions."""

    def test_session_phase_spec_accepts_required_outcomes(self) -> None:
        from omnibase_core.enums.overseer.enum_completion_outcome import (
            EnumCompletionOutcome,
        )
        from omnibase_core.models.overseer.model_session_phase_spec import (
            ModelSessionPhaseSpec,
        )

        phase = ModelSessionPhaseSpec.model_validate(
            {"phase_name": "merge", "required_outcomes": ["success"]}
        )
        assert phase.required_outcomes == (EnumCompletionOutcome.SUCCESS,)

    def test_session_phase_spec_required_outcomes_defaults_to_empty(self) -> None:
        from omnibase_core.models.overseer.model_session_phase_spec import (
            ModelSessionPhaseSpec,
        )

        phase = ModelSessionPhaseSpec(phase_name="merge")
        assert phase.required_outcomes == ()

    def test_session_phase_spec_accepts_halt_conditions(self) -> None:
        from omnibase_core.models.overseer.model_session_halt_condition import (
            ModelSessionHaltCondition,
        )
        from omnibase_core.models.overseer.model_session_phase_spec import (
            ModelSessionPhaseSpec,
        )

        halt = ModelSessionHaltCondition(
            condition_id="phase-cost-cap",
            description="Stop if phase exceeds cost",
            check_type="cost_ceiling",
            threshold=2.0,
        )
        phase = ModelSessionPhaseSpec(phase_name="merge", halt_conditions=(halt,))
        assert len(phase.halt_conditions) == 1
        assert phase.halt_conditions[0].condition_id == "phase-cost-cap"

    def test_session_phase_spec_halt_conditions_defaults_to_empty(self) -> None:
        from omnibase_core.models.overseer.model_session_phase_spec import (
            ModelSessionPhaseSpec,
        )

        phase = ModelSessionPhaseSpec(phase_name="merge")
        assert phase.halt_conditions == ()

    def test_session_phase_spec_is_frozen(self) -> None:
        from omnibase_core.models.overseer.model_session_phase_spec import (
            ModelSessionPhaseSpec,
        )

        phase = ModelSessionPhaseSpec(phase_name="merge")
        with pytest.raises(Exception):
            phase.phase_name = "other"  # type: ignore[misc]  # NOTE(OMN-11225): intentional frozen-model mutation assertion
        assert phase.phase_name == "merge"


@pytest.mark.unit
class TestSessionHaltConditionExpanded:
    """ModelSessionHaltCondition must support on_halt, skill, and full check_type set."""

    def test_session_halt_condition_accepts_on_halt_dispatch_skill(self) -> None:
        from omnibase_core.models.overseer.model_session_halt_condition import (
            ModelSessionHaltCondition,
        )

        halt = ModelSessionHaltCondition(
            condition_id="recover",
            description="Dispatch recovery skill",
            check_type="cost_ceiling",
            threshold=1.0,
            on_halt="dispatch_skill",
            skill="/onex:system_status",
        )
        assert halt.on_halt == "dispatch_skill"
        assert halt.skill == "/onex:system_status"

    def test_session_halt_condition_dispatch_skill_requires_skill_field(self) -> None:
        from omnibase_core.models.overseer.model_session_halt_condition import (
            ModelSessionHaltCondition,
        )

        with pytest.raises(ValidationError):
            ModelSessionHaltCondition(
                condition_id="recover",
                description="Missing skill",
                check_type="cost_ceiling",
                threshold=1.0,
                on_halt="dispatch_skill",
            )

    def test_session_halt_condition_accepts_pr_blocked_check_type(self) -> None:
        from omnibase_core.models.overseer.model_session_halt_condition import (
            ModelSessionHaltCondition,
        )

        halt = ModelSessionHaltCondition(
            condition_id="pr-stall",
            description="PR stalled too long",
            check_type="pr_blocked_too_long",
            threshold=0.0,
            pr=42,
            threshold_minutes=30.0,
        )
        assert halt.pr == 42
        assert halt.threshold_minutes == pytest.approx(30.0)

    def test_session_halt_condition_accepts_required_outcome_missing_type(
        self,
    ) -> None:
        from omnibase_core.models.overseer.model_session_halt_condition import (
            ModelSessionHaltCondition,
        )

        halt = ModelSessionHaltCondition(
            condition_id="outcome-missing",
            description="Required outcome not observed",
            check_type="required_outcome_missing",
            threshold=0.0,
            outcome="merge_sweep_completed",
        )
        assert halt.outcome == "merge_sweep_completed"

    def test_session_halt_condition_defaults_on_halt_to_hard_halt(self) -> None:
        from omnibase_core.models.overseer.model_session_halt_condition import (
            ModelSessionHaltCondition,
        )

        halt = ModelSessionHaltCondition(
            condition_id="cost",
            description="Cost ceiling",
            check_type="cost_ceiling",
            threshold=5.0,
        )
        assert halt.on_halt == "hard_halt"

    def test_session_halt_condition_threshold_checks_require_positive_value(
        self,
    ) -> None:
        from omnibase_core.models.overseer.model_session_halt_condition import (
            ModelSessionHaltCondition,
        )

        with pytest.raises(ValidationError):
            ModelSessionHaltCondition(
                condition_id="cost",
                description="Cost ceiling",
                check_type="cost_ceiling",
                threshold=0.0,
            )

    def test_session_halt_condition_pr_blocked_requires_positive_values(self) -> None:
        from omnibase_core.models.overseer.model_session_halt_condition import (
            ModelSessionHaltCondition,
        )

        with pytest.raises(ValidationError):
            ModelSessionHaltCondition(
                condition_id="pr-stall",
                description="PR stalled too long",
                check_type="pr_blocked_too_long",
                threshold=0.0,
                pr=0,
                threshold_minutes=30.0,
            )
        with pytest.raises(ValidationError):
            ModelSessionHaltCondition(
                condition_id="pr-stall",
                description="PR stalled too long",
                check_type="pr_blocked_too_long",
                threshold=0.0,
                pr=42,
                threshold_minutes=0.0,
            )


@pytest.mark.unit
class TestOvernightModelsDeleted:
    """Overnight-specific model files must not exist post-unification."""

    def test_model_overnight_contract_not_importable(self) -> None:
        with pytest.raises(ImportError):
            from omnibase_core.models.overseer import (
                model_overnight_contract,  # noqa: F401
            )

    def test_model_overnight_phase_spec_not_importable(self) -> None:
        with pytest.raises(ImportError):
            from omnibase_core.models.overseer import (
                model_overnight_phase_spec,  # noqa: F401
            )

    def test_model_overnight_halt_condition_not_importable(self) -> None:
        with pytest.raises(ImportError):
            from omnibase_core.models.overseer import (
                model_overnight_halt_condition,  # noqa: F401
            )


@pytest.mark.unit
class TestSessionContractBackwardsCompat:
    """Existing ModelSessionContract fields must continue to work."""

    def test_session_contract_basic_construction(self) -> None:
        from omnibase_core.models.overseer.model_session_contract import (
            ModelSessionContract,
        )
        from omnibase_core.models.overseer.model_session_phase_spec import (
            ModelSessionPhaseSpec,
        )

        contract = ModelSessionContract(
            session_id="session-1",
            created_at=datetime.now(UTC),
            phases=(ModelSessionPhaseSpec(phase_name="merge"),),
        )
        assert contract.session_id == "session-1"
        assert len(contract.phases) == 1

    def test_session_contract_default_halt_conditions_populated(self) -> None:
        from omnibase_core.models.overseer.model_session_contract import (
            ModelSessionContract,
        )
        from omnibase_core.models.overseer.model_session_phase_spec import (
            ModelSessionPhaseSpec,
        )

        contract = ModelSessionContract(
            session_id="session-2",
            created_at=datetime.now(UTC),
            max_cost_usd=7.5,
            phases=(ModelSessionPhaseSpec(phase_name="review"),),
        )
        assert len(contract.halt_conditions) == 2
        assert contract.halt_conditions[0].condition_id == "cost_ceiling"
        assert contract.halt_conditions[0].threshold == pytest.approx(7.5)

    def test_session_contract_required_outcomes_default(self) -> None:
        from omnibase_core.models.overseer.model_session_contract import (
            ModelSessionContract,
        )
        from omnibase_core.models.overseer.model_session_phase_spec import (
            ModelSessionPhaseSpec,
        )

        contract = ModelSessionContract(
            session_id="session-3",
            created_at=datetime.now(UTC),
            phases=(ModelSessionPhaseSpec(phase_name="deploy"),),
        )
        assert "merge_sweep_completed" in contract.required_outcomes
        assert "platform_readiness_gate_passed" in contract.required_outcomes


@pytest.mark.unit
class TestOMN11269AcceptanceCriteria:
    """Acceptance criteria for OMN-11269: unify ModelSessionContract and ModelOvernightContract."""

    def test_phase_spec_required_outcomes_is_typed_enum_tuple(self) -> None:
        """required_outcomes uses EnumCompletionOutcome, not bare str."""
        from omnibase_core.enums.overseer.enum_completion_outcome import (
            EnumCompletionOutcome,
        )
        from omnibase_core.models.overseer.model_session_phase_spec import (
            ModelSessionPhaseSpec,
        )

        phase = ModelSessionPhaseSpec(
            phase_name="merge",
            required_outcomes=(EnumCompletionOutcome.SUCCESS,),
        )
        assert isinstance(phase.required_outcomes, tuple)
        assert phase.required_outcomes[0] is EnumCompletionOutcome.SUCCESS

    def test_phase_spec_halt_conditions_per_phase(self) -> None:
        """Per-phase halt_conditions are supported on ModelSessionPhaseSpec."""
        from omnibase_core.models.overseer.model_session_halt_condition import (
            ModelSessionHaltCondition,
        )
        from omnibase_core.models.overseer.model_session_phase_spec import (
            ModelSessionPhaseSpec,
        )

        phase_halt = ModelSessionHaltCondition(
            condition_id="phase-pr-stall",
            description="PR blocked too long during this phase",
            check_type="pr_blocked_too_long",
            threshold=0.0,
            pr=123,
            threshold_minutes=60.0,
        )
        phase = ModelSessionPhaseSpec(
            phase_name="ci_watch",
            halt_conditions=(phase_halt,),
        )
        assert len(phase.halt_conditions) == 1
        assert phase.halt_conditions[0].check_type == "pr_blocked_too_long"

    def test_session_contract_full_overnight_equivalent(self) -> None:
        """ModelSessionContract accepts all fields ModelOvernightContract had."""
        from datetime import UTC, datetime

        from omnibase_core.enums.overseer.enum_completion_outcome import (
            EnumCompletionOutcome,
        )
        from omnibase_core.models.overseer.model_session_contract import (
            ModelSessionContract,
        )
        from omnibase_core.models.overseer.model_session_halt_condition import (
            ModelSessionHaltCondition,
        )
        from omnibase_core.models.overseer.model_session_phase_spec import (
            ModelSessionPhaseSpec,
        )

        contract = ModelSessionContract(
            session_id="omn-11269-acceptance",
            created_at=datetime.now(UTC),
            max_cost_usd=10.0,
            max_duration_seconds=28800,
            dry_run=False,
            standing_orders=("merge PRs", "watch CI"),
            required_outcomes=(
                "merge_sweep_completed",
                "platform_readiness_gate_passed",
            ),
            phases=(
                ModelSessionPhaseSpec(
                    phase_name="merge",
                    required_outcomes=(EnumCompletionOutcome.SUCCESS,),
                    halt_conditions=(
                        ModelSessionHaltCondition(
                            condition_id="phase-cost",
                            description="Phase cost ceiling",
                            check_type="cost_ceiling",
                            threshold=2.0,
                        ),
                    ),
                ),
            ),
            halt_conditions=(
                ModelSessionHaltCondition(
                    condition_id="cost_ceiling",
                    description="Global cost ceiling",
                    check_type="cost_ceiling",
                    threshold=10.0,
                ),
            ),
        )
        assert contract.phases[0].required_outcomes == (EnumCompletionOutcome.SUCCESS,)
        assert len(contract.phases[0].halt_conditions) == 1
        assert contract.standing_orders == ("merge PRs", "watch CI")
