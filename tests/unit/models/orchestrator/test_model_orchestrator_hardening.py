import pytest

# SPDX-FileCopyrightText: 2024 OmniNode Team
#
# SPDX-License-Identifier: Apache-2.0
"""
Tests for NodeOrchestrator model hardening (frozen + extra=forbid).

Verifies that ModelAction and ModelWorkflowCoordinationSubcontract
are properly hardened with frozen=True and extra="forbid".

These tests ensure:
- Models are immutable after creation (frozen=True)
- Extra fields are rejected at instantiation (extra="forbid")
- Field constraints are properly enforced
"""

from uuid import uuid4

from pydantic import ValidationError

from omnibase_core.enums.enum_workflow_execution import EnumActionType
from omnibase_core.models.contracts.subcontracts.model_workflow_coordination_subcontract import (
    ModelWorkflowCoordinationSubcontract,
)
from omnibase_core.models.orchestrator.model_action import ModelAction
from omnibase_core.models.primitives.model_semver import ModelSemVer

# Default version for test instances - required field
DEFAULT_VERSION = ModelSemVer(major=1, minor=0, patch=0)


@pytest.mark.timeout(30)
@pytest.mark.unit
class TestModelActionHardening:
    """Tests for ModelAction frozen and extra=forbid."""

    def test_is_frozen(self) -> None:
        """Verify ModelAction is immutable after creation."""
        action = ModelAction(
            action_type=EnumActionType.COMPUTE,
            target_node_type="COMPUTE",
            lease_id=uuid4(),
            epoch=1,
        )
        with pytest.raises(ValidationError):
            action.action_type = EnumActionType.EFFECT  # type: ignore[misc]

    def test_extra_fields_rejected(self) -> None:
        """Verify extra fields are rejected."""
        with pytest.raises(ValidationError) as exc_info:
            ModelAction(
                action_type=EnumActionType.COMPUTE,
                target_node_type="COMPUTE",
                lease_id=uuid4(),
                epoch=1,
                unknown_field="should_fail",  # type: ignore[call-arg]
            )
        assert (
            "extra" in str(exc_info.value).lower()
            or "unexpected" in str(exc_info.value).lower()
        )

    def test_priority_bounds(self) -> None:
        """Verify priority constraints (ge=1, le=10)."""
        # Valid priority
        valid = ModelAction(
            action_type=EnumActionType.COMPUTE,
            target_node_type="COMPUTE",
            lease_id=uuid4(),
            epoch=1,
            priority=5,
        )
        assert valid.priority == 5

        # Too small (must be >= 1)
        with pytest.raises(ValidationError):
            ModelAction(
                action_type=EnumActionType.COMPUTE,
                target_node_type="COMPUTE",
                lease_id=uuid4(),
                epoch=1,
                priority=0,
            )

        # Too large (must be <= 10)
        with pytest.raises(ValidationError):
            ModelAction(
                action_type=EnumActionType.COMPUTE,
                target_node_type="COMPUTE",
                lease_id=uuid4(),
                epoch=1,
                priority=11,
            )

    def test_timeout_ms_bounds(self) -> None:
        """Verify timeout_ms constraints (ge=100, le=300000)."""
        # Valid timeout
        valid = ModelAction(
            action_type=EnumActionType.COMPUTE,
            target_node_type="COMPUTE",
            lease_id=uuid4(),
            epoch=1,
            timeout_ms=60000,
        )
        assert valid.timeout_ms == 60000

        # Too small (must be >= 100)
        with pytest.raises(ValidationError):
            ModelAction(
                action_type=EnumActionType.COMPUTE,
                target_node_type="COMPUTE",
                lease_id=uuid4(),
                epoch=1,
                timeout_ms=99,
            )

        # Too large (must be <= 300000)
        with pytest.raises(ValidationError):
            ModelAction(
                action_type=EnumActionType.COMPUTE,
                target_node_type="COMPUTE",
                lease_id=uuid4(),
                epoch=1,
                timeout_ms=300001,
            )

    def test_retry_count_bounds(self) -> None:
        """Verify retry_count constraints (ge=0, le=10)."""
        # Valid retry count
        valid = ModelAction(
            action_type=EnumActionType.COMPUTE,
            target_node_type="COMPUTE",
            lease_id=uuid4(),
            epoch=1,
            retry_count=5,
        )
        assert valid.retry_count == 5

        # Negative (must be >= 0)
        with pytest.raises(ValidationError):
            ModelAction(
                action_type=EnumActionType.COMPUTE,
                target_node_type="COMPUTE",
                lease_id=uuid4(),
                epoch=1,
                retry_count=-1,
            )

        # Too large (must be <= 10)
        with pytest.raises(ValidationError):
            ModelAction(
                action_type=EnumActionType.COMPUTE,
                target_node_type="COMPUTE",
                lease_id=uuid4(),
                epoch=1,
                retry_count=11,
            )

    def test_epoch_bounds(self) -> None:
        """Verify epoch constraints (ge=0)."""
        # Valid epoch (0 is allowed)
        valid = ModelAction(
            action_type=EnumActionType.COMPUTE,
            target_node_type="COMPUTE",
            lease_id=uuid4(),
            epoch=0,
        )
        assert valid.epoch == 0

        # Negative epoch should fail
        with pytest.raises(ValidationError):
            ModelAction(
                action_type=EnumActionType.COMPUTE,
                target_node_type="COMPUTE",
                lease_id=uuid4(),
                epoch=-1,
            )

    def test_target_node_type_length_bounds(self) -> None:
        """Verify target_node_type length constraints (min=1, max=100)."""
        # Valid target_node_type
        valid = ModelAction(
            action_type=EnumActionType.COMPUTE,
            target_node_type="COMPUTE",
            lease_id=uuid4(),
            epoch=1,
        )
        assert valid.target_node_type == "COMPUTE"

        # Too short (must be >= 1)
        with pytest.raises(ValidationError):
            ModelAction(
                action_type=EnumActionType.COMPUTE,
                target_node_type="",
                lease_id=uuid4(),
                epoch=1,
            )

        # Too long (must be <= 100)
        with pytest.raises(ValidationError):
            ModelAction(
                action_type=EnumActionType.COMPUTE,
                target_node_type="x" * 101,
                lease_id=uuid4(),
                epoch=1,
            )

    def test_model_config_frozen(self) -> None:
        """Verify model_config has frozen=True."""
        config = ModelAction.model_config
        assert config.get("frozen") is True

    def test_model_config_extra_forbid(self) -> None:
        """Verify model_config has extra='forbid'."""
        config = ModelAction.model_config
        assert config.get("extra") == "forbid"

    def test_model_copy_for_modifications(self) -> None:
        """Verify model_copy can be used to create modified copies."""
        original = ModelAction(
            action_type=EnumActionType.COMPUTE,
            target_node_type="COMPUTE",
            lease_id=uuid4(),
            epoch=1,
            priority=5,
        )

        # Create a modified copy (this is the correct pattern for frozen models)
        modified = original.model_copy(update={"priority": 8})

        assert original.priority == 5  # Original unchanged
        assert modified.priority == 8  # Copy has new value
        assert original.action_type == modified.action_type  # Other fields preserved


@pytest.mark.timeout(30)
@pytest.mark.unit
class TestModelWorkflowCoordinationSubcontractHardening:
    """Tests for ModelWorkflowCoordinationSubcontract frozen and extra=forbid."""

    def test_is_frozen(self) -> None:
        """Verify ModelWorkflowCoordinationSubcontract is immutable after creation."""
        subcontract = ModelWorkflowCoordinationSubcontract(
            version=DEFAULT_VERSION,
            subcontract_version=DEFAULT_VERSION,
        )
        with pytest.raises(ValidationError):
            subcontract.max_concurrent_workflows = 20  # type: ignore[misc]

    def test_extra_fields_rejected(self) -> None:
        """Verify extra fields are rejected."""
        with pytest.raises(ValidationError) as exc_info:
            ModelWorkflowCoordinationSubcontract(
                version=DEFAULT_VERSION,
                subcontract_version=DEFAULT_VERSION,
                unknown_field="should_fail",  # type: ignore[call-arg]
            )
        assert (
            "extra" in str(exc_info.value).lower()
            or "unexpected" in str(exc_info.value).lower()
        )

    def test_timeout_bounds(self) -> None:
        """Verify default_workflow_timeout_ms constraints (ge=60000, le=3600000)."""
        # Valid timeout
        valid = ModelWorkflowCoordinationSubcontract(
            version=DEFAULT_VERSION,
            subcontract_version=DEFAULT_VERSION,
            default_workflow_timeout_ms=1800000,  # 30 minutes
        )
        assert valid.default_workflow_timeout_ms == 1800000

        # Too small (must be >= 60000)
        with pytest.raises(ValidationError):
            ModelWorkflowCoordinationSubcontract(
                version=DEFAULT_VERSION,
                subcontract_version=DEFAULT_VERSION,
                default_workflow_timeout_ms=59999,
            )

        # Too large (must be <= 3600000)
        with pytest.raises(ValidationError):
            ModelWorkflowCoordinationSubcontract(
                version=DEFAULT_VERSION,
                subcontract_version=DEFAULT_VERSION,
                default_workflow_timeout_ms=3600001,
            )

    def test_max_concurrent_workflows_bounds(self) -> None:
        """Verify max_concurrent_workflows constraints (ge=1, le=100)."""
        # Valid value
        valid = ModelWorkflowCoordinationSubcontract(
            version=DEFAULT_VERSION,
            subcontract_version=DEFAULT_VERSION,
            max_concurrent_workflows=50,
        )
        assert valid.max_concurrent_workflows == 50

        # Too small (must be >= 1)
        with pytest.raises(ValidationError):
            ModelWorkflowCoordinationSubcontract(
                version=DEFAULT_VERSION,
                subcontract_version=DEFAULT_VERSION,
                max_concurrent_workflows=0,
            )

        # Too large (must be <= 100)
        with pytest.raises(ValidationError):
            ModelWorkflowCoordinationSubcontract(
                version=DEFAULT_VERSION,
                subcontract_version=DEFAULT_VERSION,
                max_concurrent_workflows=101,
            )

    def test_node_coordination_timeout_ms_bounds(self) -> None:
        """Verify node_coordination_timeout_ms constraints (ge=5000, le=300000)."""
        # Valid value
        valid = ModelWorkflowCoordinationSubcontract(
            version=DEFAULT_VERSION,
            subcontract_version=DEFAULT_VERSION,
            node_coordination_timeout_ms=60000,
        )
        assert valid.node_coordination_timeout_ms == 60000

        # Too small (must be >= 5000)
        with pytest.raises(ValidationError):
            ModelWorkflowCoordinationSubcontract(
                version=DEFAULT_VERSION,
                subcontract_version=DEFAULT_VERSION,
                node_coordination_timeout_ms=4999,
            )

        # Too large (must be <= 300000)
        with pytest.raises(ValidationError):
            ModelWorkflowCoordinationSubcontract(
                version=DEFAULT_VERSION,
                subcontract_version=DEFAULT_VERSION,
                node_coordination_timeout_ms=300001,
            )

    def test_checkpoint_interval_ms_bounds(self) -> None:
        """Verify checkpoint_interval_ms constraints (ge=10000, le=600000)."""
        # Valid value
        valid = ModelWorkflowCoordinationSubcontract(
            version=DEFAULT_VERSION,
            subcontract_version=DEFAULT_VERSION,
            checkpoint_interval_ms=120000,
        )
        assert valid.checkpoint_interval_ms == 120000

        # Too small (must be >= 10000)
        with pytest.raises(ValidationError):
            ModelWorkflowCoordinationSubcontract(
                version=DEFAULT_VERSION,
                subcontract_version=DEFAULT_VERSION,
                checkpoint_interval_ms=9999,
            )

        # Too large (must be <= 600000)
        with pytest.raises(ValidationError):
            ModelWorkflowCoordinationSubcontract(
                version=DEFAULT_VERSION,
                subcontract_version=DEFAULT_VERSION,
                checkpoint_interval_ms=600001,
            )

    def test_max_retries_bounds(self) -> None:
        """Verify max_retries constraints (ge=0, le=10)."""
        # Valid value
        valid = ModelWorkflowCoordinationSubcontract(
            version=DEFAULT_VERSION,
            subcontract_version=DEFAULT_VERSION,
            max_retries=5,
        )
        assert valid.max_retries == 5

        # Negative (must be >= 0)
        with pytest.raises(ValidationError):
            ModelWorkflowCoordinationSubcontract(
                version=DEFAULT_VERSION,
                subcontract_version=DEFAULT_VERSION,
                max_retries=-1,
            )

        # Too large (must be <= 10)
        with pytest.raises(ValidationError):
            ModelWorkflowCoordinationSubcontract(
                version=DEFAULT_VERSION,
                subcontract_version=DEFAULT_VERSION,
                max_retries=11,
            )

    def test_retry_delay_ms_bounds(self) -> None:
        """Verify retry_delay_ms constraints (ge=1000, le=60000)."""
        # Valid value
        valid = ModelWorkflowCoordinationSubcontract(
            version=DEFAULT_VERSION,
            subcontract_version=DEFAULT_VERSION,
            retry_delay_ms=5000,
        )
        assert valid.retry_delay_ms == 5000

        # Too small (must be >= 1000)
        with pytest.raises(ValidationError):
            ModelWorkflowCoordinationSubcontract(
                version=DEFAULT_VERSION,
                subcontract_version=DEFAULT_VERSION,
                retry_delay_ms=999,
            )

        # Too large (must be <= 60000)
        with pytest.raises(ValidationError):
            ModelWorkflowCoordinationSubcontract(
                version=DEFAULT_VERSION,
                subcontract_version=DEFAULT_VERSION,
                retry_delay_ms=60001,
            )

    def test_model_config_frozen(self) -> None:
        """Verify model_config has frozen=True."""
        config = ModelWorkflowCoordinationSubcontract.model_config
        assert config.get("frozen") is True

    def test_model_config_extra_forbid(self) -> None:
        """Verify model_config has extra='forbid'."""
        config = ModelWorkflowCoordinationSubcontract.model_config
        assert config.get("extra") == "forbid"

    def test_interface_version_accessible(self) -> None:
        """Test INTERFACE_VERSION is accessible as ClassVar."""
        assert hasattr(ModelWorkflowCoordinationSubcontract, "INTERFACE_VERSION")
        assert isinstance(
            ModelWorkflowCoordinationSubcontract.INTERFACE_VERSION, ModelSemVer
        )
        assert ModelWorkflowCoordinationSubcontract.INTERFACE_VERSION.major == 1
        assert ModelWorkflowCoordinationSubcontract.INTERFACE_VERSION.minor == 0
        assert ModelWorkflowCoordinationSubcontract.INTERFACE_VERSION.patch == 0

    def test_model_copy_for_modifications(self) -> None:
        """Verify model_copy can be used to create modified copies."""
        original = ModelWorkflowCoordinationSubcontract(
            version=DEFAULT_VERSION,
            subcontract_version=DEFAULT_VERSION,
            max_concurrent_workflows=10,
        )

        # Create a modified copy (this is the correct pattern for frozen models)
        modified = original.model_copy(update={"max_concurrent_workflows": 20})

        assert original.max_concurrent_workflows == 10  # Original unchanged
        assert modified.max_concurrent_workflows == 20  # Copy has new value
        assert original.version == modified.version  # Other fields preserved
