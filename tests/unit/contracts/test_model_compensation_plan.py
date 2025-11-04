#!/usr/bin/env python3
"""
ModelCompensationPlan Comprehensive Unit Tests - Zero Tolerance Testing

This module provides comprehensive test coverage for ModelCompensationPlan,
the strongly-typed compensation plan model for saga pattern workflows.

Coverage Requirements:
- >95% line coverage for all methods
- 100% coverage for error handling paths
- Comprehensive validation scenarios
- UUID and action identifier validation

ZERO TOLERANCE: Every code path must be tested thoroughly.
"""

from uuid import UUID, uuid4

import pytest

from omnibase_core.enums.enum_compensation_strategy import EnumCompensationStrategy
from omnibase_core.enums.enum_execution_order import EnumExecutionOrder
from omnibase_core.errors.error_codes import EnumCoreErrorCode
from omnibase_core.models.contracts.model_compensation_plan import ModelCompensationPlan
from omnibase_core.models.errors.model_onex_error import ModelOnexError as OnexError


class TestModelCompensationPlan:
    """Comprehensive tests for ModelCompensationPlan with zero tolerance coverage."""

    def setup_method(self):
        """Set up test fixtures for each test method."""
        self.valid_plan_id = uuid4()
        self.minimal_valid_data = {
            "plan_id": self.valid_plan_id,
            "plan_name": "test_compensation_plan",
        }

    # =================== VALID CONSTRUCTION TESTS ===================

    def test_valid_construction_minimal_fields(self):
        """Test valid construction with minimal required fields."""
        plan = ModelCompensationPlan(**self.minimal_valid_data)

        assert plan.plan_id == self.valid_plan_id
        assert plan.plan_name == "test_compensation_plan"
        assert plan.trigger_on_failure is True
        assert plan.trigger_on_timeout is True
        assert plan.trigger_on_cancellation is True
        assert plan.compensation_strategy == EnumCompensationStrategy.ROLLBACK
        assert plan.execution_order == EnumExecutionOrder.REVERSE

    def test_valid_construction_all_fields(self):
        """Test valid construction with all fields populated."""
        plan_id = uuid4()
        depends_on_id_1 = uuid4()
        depends_on_id_2 = uuid4()

        full_data = {
            "plan_id": plan_id,
            "plan_name": "comprehensive_plan",
            "trigger_on_failure": False,
            "trigger_on_timeout": False,
            "trigger_on_cancellation": False,
            "compensation_strategy": EnumCompensationStrategy.FORWARD_RECOVERY,
            "execution_order": EnumExecutionOrder.FORWARD,
            "total_timeout_ms": 60000,
            "action_timeout_ms": 10000,
            "rollback_actions": ["rollback_payment", "rollback_inventory"],
            "cleanup_actions": ["cleanup_temp_files", "cleanup_cache"],
            "notification_actions": ["notify_admin", "notify_user"],
            "recovery_actions": ["retry_operation", "escalate_to_manual"],
            "continue_on_compensation_failure": True,
            "max_compensation_retries": 5,
            "audit_compensation": False,
            "log_level": "debug",
            "partial_compensation_allowed": True,
            "idempotent_actions": False,
            "depends_on_plans": [depends_on_id_1, depends_on_id_2],
            "priority": 500,
            "delay_before_execution_ms": 1000,
        }

        plan = ModelCompensationPlan(**full_data)

        assert plan.plan_id == plan_id
        assert plan.trigger_on_failure is False
        assert plan.compensation_strategy == EnumCompensationStrategy.FORWARD_RECOVERY
        assert plan.execution_order == EnumExecutionOrder.FORWARD
        assert plan.total_timeout_ms == 60000
        assert plan.action_timeout_ms == 10000
        assert len(plan.rollback_actions) == 2
        assert len(plan.cleanup_actions) == 2
        assert len(plan.notification_actions) == 2
        assert len(plan.recovery_actions) == 2
        assert plan.continue_on_compensation_failure is True
        assert plan.max_compensation_retries == 5
        assert plan.audit_compensation is False
        assert plan.log_level == "debug"
        assert plan.partial_compensation_allowed is True
        assert plan.idempotent_actions is False
        assert len(plan.depends_on_plans) == 2
        assert plan.priority == 500
        assert plan.delay_before_execution_ms == 1000

    # =================== PLAN_ID VALIDATION TESTS ===================

    def test_validate_plan_id_with_valid_uuid_object(self):
        """Test plan_id validation with valid UUID object."""
        plan_id = uuid4()
        plan = ModelCompensationPlan(
            plan_id=plan_id,
            plan_name="test_plan",
        )

        assert plan.plan_id == plan_id
        assert isinstance(plan.plan_id, UUID)

    def test_validate_plan_id_with_valid_uuid_string(self):
        """Test plan_id validation with valid UUID string."""
        plan_id = uuid4()
        plan = ModelCompensationPlan(
            plan_id=str(plan_id),
            plan_name="test_plan",
        )

        assert plan.plan_id == plan_id
        assert isinstance(plan.plan_id, UUID)

    def test_validate_plan_id_with_empty_string(self):
        """Test plan_id validation fails with empty string."""
        with pytest.raises(OnexError) as exc_info:
            ModelCompensationPlan(
                plan_id="",
                plan_name="test_plan",
            )

        assert exc_info.value.error_code == EnumCoreErrorCode.VALIDATION_ERROR
        assert "Plan ID cannot be empty" in str(exc_info.value)

    def test_validate_plan_id_with_whitespace_string(self):
        """Test plan_id validation fails with whitespace-only string."""
        with pytest.raises(OnexError) as exc_info:
            ModelCompensationPlan(
                plan_id="   ",
                plan_name="test_plan",
            )

        assert exc_info.value.error_code == EnumCoreErrorCode.VALIDATION_ERROR
        assert "Plan ID cannot be empty" in str(exc_info.value)

    def test_validate_plan_id_with_invalid_uuid_string(self):
        """Test plan_id validation fails with invalid UUID string."""
        with pytest.raises(OnexError) as exc_info:
            ModelCompensationPlan(
                plan_id="not-a-valid-uuid",
                plan_name="test_plan",
            )

        assert exc_info.value.error_code == EnumCoreErrorCode.VALIDATION_ERROR
        assert "Invalid plan_id" in str(exc_info.value)
        assert "Must be a valid UUID" in str(exc_info.value)

    # =================== ACTION LISTS VALIDATION TESTS ===================

    def test_validate_action_lists_with_valid_identifiers(self):
        """Test action lists validation with valid identifiers."""
        plan = ModelCompensationPlan(
            plan_id=uuid4(),
            plan_name="test_plan",
            rollback_actions=["action_1", "action-2", "action_three"],
            cleanup_actions=["cleanup-1", "cleanup_2"],
            notification_actions=["notify_admin"],
            recovery_actions=["retry-operation"],
        )

        assert len(plan.rollback_actions) == 3
        assert len(plan.cleanup_actions) == 2
        assert len(plan.notification_actions) == 1
        assert len(plan.recovery_actions) == 1

    def test_validate_action_lists_with_empty_entries(self):
        """Test action lists validation skips empty entries."""
        plan = ModelCompensationPlan(
            plan_id=uuid4(),
            plan_name="test_plan",
            rollback_actions=["action_1", "", "action_2", "   "],
        )

        # Empty entries should be filtered out
        assert len(plan.rollback_actions) == 2
        assert "action_1" in plan.rollback_actions
        assert "action_2" in plan.rollback_actions

    def test_validate_action_lists_with_invalid_characters(self):
        """Test action lists validation fails with invalid characters."""
        with pytest.raises(OnexError) as exc_info:
            ModelCompensationPlan(
                plan_id=uuid4(),
                plan_name="test_plan",
                rollback_actions=["valid_action", "invalid@action!"],
            )

        assert exc_info.value.error_code == EnumCoreErrorCode.VALIDATION_ERROR
        assert "Invalid action_id" in str(exc_info.value)
        assert "Must contain only alphanumeric characters" in str(exc_info.value)

    def test_validate_action_lists_with_special_characters(self):
        """Test action lists validation fails with disallowed special characters."""
        with pytest.raises(OnexError) as exc_info:
            ModelCompensationPlan(
                plan_id=uuid4(),
                plan_name="test_plan",
                cleanup_actions=["action$special"],
            )

        assert exc_info.value.error_code == EnumCoreErrorCode.VALIDATION_ERROR

    def test_validate_multiple_action_types(self):
        """Test validation across all action types."""
        plan = ModelCompensationPlan(
            plan_id=uuid4(),
            plan_name="test_plan",
            rollback_actions=["rollback-1", "rollback_2"],
            cleanup_actions=["cleanup-1"],
            notification_actions=["notify-admin"],
            recovery_actions=["retry-op"],
        )

        assert len(plan.rollback_actions) == 2
        assert len(plan.cleanup_actions) == 1
        assert len(plan.notification_actions) == 1
        assert len(plan.recovery_actions) == 1

    # =================== PLAN DEPENDENCIES VALIDATION TESTS ===================

    def test_validate_plan_dependencies_with_valid_uuids(self):
        """Test plan dependencies validation with valid UUID objects."""
        dep_id_1 = uuid4()
        dep_id_2 = uuid4()

        plan = ModelCompensationPlan(
            plan_id=uuid4(),
            plan_name="test_plan",
            depends_on_plans=[dep_id_1, dep_id_2],
        )

        assert len(plan.depends_on_plans) == 2
        assert dep_id_1 in plan.depends_on_plans
        assert dep_id_2 in plan.depends_on_plans

    def test_validate_plan_dependencies_with_uuid_strings(self):
        """Test plan dependencies validation with valid UUID strings."""
        dep_id_1 = uuid4()
        dep_id_2 = uuid4()

        plan = ModelCompensationPlan(
            plan_id=uuid4(),
            plan_name="test_plan",
            depends_on_plans=[str(dep_id_1), str(dep_id_2)],
        )

        assert len(plan.depends_on_plans) == 2
        assert dep_id_1 in plan.depends_on_plans
        assert dep_id_2 in plan.depends_on_plans

    def test_validate_plan_dependencies_with_mixed_types(self):
        """Test plan dependencies validation with mixed UUID objects and strings."""
        dep_id_1 = uuid4()
        dep_id_2 = uuid4()

        plan = ModelCompensationPlan(
            plan_id=uuid4(),
            plan_name="test_plan",
            depends_on_plans=[dep_id_1, str(dep_id_2)],
        )

        assert len(plan.depends_on_plans) == 2
        assert dep_id_1 in plan.depends_on_plans
        assert dep_id_2 in plan.depends_on_plans

    def test_validate_plan_dependencies_with_empty_entries(self):
        """Test plan dependencies validation skips empty entries."""
        dep_id = uuid4()

        plan = ModelCompensationPlan(
            plan_id=uuid4(),
            plan_name="test_plan",
            depends_on_plans=[str(dep_id), "", "   "],
        )

        # Empty entries should be filtered out
        assert len(plan.depends_on_plans) == 1
        assert dep_id in plan.depends_on_plans

    def test_validate_plan_dependencies_with_invalid_uuid_string(self):
        """Test plan dependencies validation fails with invalid UUID string."""
        with pytest.raises(OnexError) as exc_info:
            ModelCompensationPlan(
                plan_id=uuid4(),
                plan_name="test_plan",
                depends_on_plans=["not-a-valid-uuid"],
            )

        assert exc_info.value.error_code == EnumCoreErrorCode.VALIDATION_ERROR
        assert "Invalid dependency plan_id" in str(exc_info.value)
        assert "Must be a valid UUID" in str(exc_info.value)

    # =================== FIELD CONSTRAINTS VALIDATION TESTS ===================

    def test_validate_plan_name_length_constraints(self):
        """Test plan_name length constraints."""
        # Valid length
        plan = ModelCompensationPlan(
            plan_id=uuid4(),
            plan_name="a" * 200,  # Max length
        )
        assert len(plan.plan_name) == 200

        # Too long
        with pytest.raises(Exception):  # Pydantic ValidationError
            ModelCompensationPlan(
                plan_id=uuid4(),
                plan_name="a" * 201,
            )

        # Too short (empty)
        with pytest.raises(Exception):  # Pydantic ValidationError
            ModelCompensationPlan(
                plan_id=uuid4(),
                plan_name="",
            )

    def test_validate_timeout_constraints(self):
        """Test timeout field constraints."""
        # Valid timeouts
        plan = ModelCompensationPlan(
            plan_id=uuid4(),
            plan_name="test_plan",
            total_timeout_ms=1000,  # Min
            action_timeout_ms=1000,  # Min
        )
        assert plan.total_timeout_ms == 1000
        assert plan.action_timeout_ms == 1000

        # Below minimum
        with pytest.raises(Exception):  # Pydantic ValidationError
            ModelCompensationPlan(
                plan_id=uuid4(),
                plan_name="test_plan",
                total_timeout_ms=999,
            )

        # Above maximum
        with pytest.raises(Exception):  # Pydantic ValidationError
            ModelCompensationPlan(
                plan_id=uuid4(),
                plan_name="test_plan",
                total_timeout_ms=3600001,
            )

    def test_validate_retry_constraints(self):
        """Test max_compensation_retries constraints."""
        # Valid retries
        plan = ModelCompensationPlan(
            plan_id=uuid4(),
            plan_name="test_plan",
            max_compensation_retries=0,  # Min
        )
        assert plan.max_compensation_retries == 0

        plan = ModelCompensationPlan(
            plan_id=uuid4(),
            plan_name="test_plan",
            max_compensation_retries=10,  # Max
        )
        assert plan.max_compensation_retries == 10

        # Above maximum
        with pytest.raises(Exception):  # Pydantic ValidationError
            ModelCompensationPlan(
                plan_id=uuid4(),
                plan_name="test_plan",
                max_compensation_retries=11,
            )

    def test_validate_priority_constraints(self):
        """Test priority field constraints."""
        # Valid priority
        plan = ModelCompensationPlan(
            plan_id=uuid4(),
            plan_name="test_plan",
            priority=1,  # Min
        )
        assert plan.priority == 1

        plan = ModelCompensationPlan(
            plan_id=uuid4(),
            plan_name="test_plan",
            priority=1000,  # Max
        )
        assert plan.priority == 1000

        # Below minimum
        with pytest.raises(Exception):  # Pydantic ValidationError
            ModelCompensationPlan(
                plan_id=uuid4(),
                plan_name="test_plan",
                priority=0,
            )

        # Above maximum
        with pytest.raises(Exception):  # Pydantic ValidationError
            ModelCompensationPlan(
                plan_id=uuid4(),
                plan_name="test_plan",
                priority=1001,
            )

    def test_validate_delay_constraints(self):
        """Test delay_before_execution_ms constraints."""
        # Valid delay
        plan = ModelCompensationPlan(
            plan_id=uuid4(),
            plan_name="test_plan",
            delay_before_execution_ms=0,  # Min
        )
        assert plan.delay_before_execution_ms == 0

        plan = ModelCompensationPlan(
            plan_id=uuid4(),
            plan_name="test_plan",
            delay_before_execution_ms=60000,  # Max
        )
        assert plan.delay_before_execution_ms == 60000

        # Above maximum
        with pytest.raises(Exception):  # Pydantic ValidationError
            ModelCompensationPlan(
                plan_id=uuid4(),
                plan_name="test_plan",
                delay_before_execution_ms=60001,
            )

    # =================== LOG LEVEL VALIDATION TESTS ===================

    def test_validate_log_level_literal_values(self):
        """Test log_level accepts only literal values."""
        valid_levels = ["debug", "info", "warn", "error"]

        for level in valid_levels:
            plan = ModelCompensationPlan(
                plan_id=uuid4(),
                plan_name="test_plan",
                log_level=level,
            )
            assert plan.log_level == level

        # Invalid log level
        with pytest.raises(Exception):  # Pydantic ValidationError
            ModelCompensationPlan(
                plan_id=uuid4(),
                plan_name="test_plan",
                log_level="invalid",
            )

    # =================== ENUM VALIDATION TESTS ===================

    def test_validate_compensation_strategy_enum(self):
        """Test compensation_strategy accepts enum values."""
        plan = ModelCompensationPlan(
            plan_id=uuid4(),
            plan_name="test_plan",
            compensation_strategy=EnumCompensationStrategy.FORWARD_RECOVERY,
        )
        assert plan.compensation_strategy == EnumCompensationStrategy.FORWARD_RECOVERY

    def test_validate_execution_order_enum(self):
        """Test execution_order accepts enum values."""
        plan = ModelCompensationPlan(
            plan_id=uuid4(),
            plan_name="test_plan",
            execution_order=EnumExecutionOrder.FORWARD,
        )
        assert plan.execution_order == EnumExecutionOrder.FORWARD

    # =================== COMPREHENSIVE INTEGRATION TESTS ===================

    def test_complex_compensation_plan_configuration(self):
        """Test complex compensation plan with all features configured."""
        plan_id = uuid4()
        dep_id_1 = uuid4()
        dep_id_2 = uuid4()

        plan = ModelCompensationPlan(
            plan_id=plan_id,
            plan_name="complex_saga_compensation",
            trigger_on_failure=True,
            trigger_on_timeout=True,
            trigger_on_cancellation=False,
            compensation_strategy=EnumCompensationStrategy.MIXED,
            execution_order=EnumExecutionOrder.PARALLEL,
            total_timeout_ms=120000,
            action_timeout_ms=15000,
            rollback_actions=[
                "rollback_payment",
                "rollback_inventory",
                "rollback_shipping",
            ],
            cleanup_actions=["cleanup_temp_data", "cleanup_locks"],
            notification_actions=["notify_admin", "notify_customer", "log_incident"],
            recovery_actions=["retry_with_backoff", "escalate_to_manual"],
            continue_on_compensation_failure=False,
            max_compensation_retries=3,
            audit_compensation=True,
            log_level="info",
            partial_compensation_allowed=False,
            idempotent_actions=True,
            depends_on_plans=[dep_id_1, dep_id_2],
            priority=750,
            delay_before_execution_ms=500,
        )

        assert plan.plan_id == plan_id
        assert len(plan.rollback_actions) == 3
        assert len(plan.cleanup_actions) == 2
        assert len(plan.notification_actions) == 3
        assert len(plan.recovery_actions) == 2
        assert len(plan.depends_on_plans) == 2
        assert plan.priority == 750

    def test_model_config_validate_assignment(self):
        """Test that field assignments are validated as per model_config."""
        plan = ModelCompensationPlan(**self.minimal_valid_data)

        # This should trigger validation
        with pytest.raises(Exception):
            plan.trigger_on_failure = "invalid_bool_value"

    def test_default_values(self):
        """Test that default values are properly set."""
        plan = ModelCompensationPlan(**self.minimal_valid_data)

        assert plan.trigger_on_failure is True
        assert plan.trigger_on_timeout is True
        assert plan.trigger_on_cancellation is True
        assert plan.compensation_strategy == EnumCompensationStrategy.ROLLBACK
        assert plan.execution_order == EnumExecutionOrder.REVERSE
        assert plan.total_timeout_ms == 300000
        assert plan.action_timeout_ms == 30000
        assert plan.rollback_actions == []
        assert plan.cleanup_actions == []
        assert plan.notification_actions == []
        assert plan.recovery_actions == []
        assert plan.continue_on_compensation_failure is False
        assert plan.max_compensation_retries == 3
        assert plan.audit_compensation is True
        assert plan.log_level == "info"
        assert plan.partial_compensation_allowed is False
        assert plan.idempotent_actions is True
        assert plan.depends_on_plans == []
        assert plan.priority == 100
        assert plan.delay_before_execution_ms == 0
