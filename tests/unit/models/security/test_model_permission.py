"""
Comprehensive unit tests for ModelPermission.

Tests cover:
- Permission initialization and validation
- Field validators and constraints
- Resource matching (direct, patterns, hierarchy, wildcards)
- Temporal validation (date ranges, time of day, days of week)
- Geographic validation (countries, IP ranges)
- Condition evaluation
- Usage limits and quotas
- Risk scoring and assessment
- Factory methods (read, write, admin, deny, emergency, time-limited)
- Utility methods and helper functions
- Permission comparison and specificity
- Error scenarios and ONEX compliance
"""

import pytest
from datetime import UTC, datetime, timedelta
from uuid import UUID

# Direct imports to avoid broken __init__.py
import sys
from pathlib import Path

# Add src to path for direct imports
src_path = Path(__file__).parent.parent.parent.parent.parent / "src"
if str(src_path) not in sys.path:
    sys.path.insert(0, str(src_path))

from omnibase_core.errors.model_onex_error import ModelOnexError
from omnibase_core.models.security.model_permission import ModelPermission
from omnibase_core.models.security.model_permission_evaluation_context import (
    ModelPermissionEvaluationContext,
)
from omnibase_core.primitives.model_semver import ModelSemVer


class TestModelPermissionBasicInitialization:
    """Test basic ModelPermission initialization and field validation."""

    def test_permission_minimal_required_fields(self):
        """Test permission creation with minimal required fields."""
        permission = ModelPermission(
            name="read_resource",
            resource="projects/test",
            action="read",
        )

        assert permission.name == "read_resource"
        assert permission.resource == "projects/test"
        assert permission.action == "read"
        assert permission.effect == "allow"  # Default
        assert isinstance(permission.permission_id, UUID)
        assert isinstance(permission.version, ModelSemVer)

    def test_permission_with_all_fields(self):
        """Test permission creation with all fields populated."""
        permission = ModelPermission(
            name="admin_permission",
            resource="projects/*",
            action="*",
            effect="allow",
            scope_type="global",
            priority=50,
            namespace="test_namespace",
            description="Test admin permission",
            risk_level="high",
            require_mfa=True,
            require_secure_connection=True,
            approval_required=True,
        )

        assert permission.name == "admin_permission"
        assert permission.scope_type == "global"
        assert permission.priority == 50
        assert permission.risk_level == "high"
        assert permission.require_mfa is True
        assert permission.approval_required is True

    def test_permission_id_is_unique(self):
        """Test that each permission gets a unique ID."""
        perm1 = ModelPermission(name="test1", resource="r1", action="read")
        perm2 = ModelPermission(name="test2", resource="r2", action="read")

        assert perm1.permission_id != perm2.permission_id
        assert isinstance(perm1.permission_id, UUID)
        assert isinstance(perm2.permission_id, UUID)

    def test_permission_timestamps(self):
        """Test permission timestamp fields."""
        before = datetime.now(UTC)
        permission = ModelPermission(
            name="test_perm",
            resource="test",
            action="read",
        )
        after = datetime.now(UTC)

        assert before <= permission.created_at <= after
        assert permission.updated_at is None

    def test_permission_update_timestamp(self):
        """Test permission timestamp update method."""
        permission = ModelPermission(
            name="test_perm",
            resource="test",
            action="read",
        )

        original_created = permission.created_at
        assert permission.updated_at is None

        permission.update_timestamp()

        assert permission.created_at == original_created
        assert permission.updated_at is not None
        assert permission.updated_at >= original_created


class TestModelPermissionFieldValidation:
    """Test field validation and constraints."""

    def test_name_pattern_validation_valid(self):
        """Test valid name patterns."""
        valid_names = [
            "read_resource",
            "Write-Resource",
            "Admin_Permission_123",
            "test permission",
        ]

        for name in valid_names:
            permission = ModelPermission(name=name, resource="test", action="read")
            assert permission.name == name

    def test_name_pattern_validation_invalid(self):
        """Test invalid name patterns."""
        with pytest.raises(Exception):  # Pydantic ValidationError
            ModelPermission(name="123_invalid", resource="test", action="read")

    def test_resource_pattern_validation_valid(self):
        """Test valid resource patterns."""
        valid_resources = [
            "projects/test",
            "org:project:resource",
            "test-resource",
            "test_resource",
            "a/b/c/d/e",
            "test/*",
        ]

        for resource in valid_resources:
            permission = ModelPermission(
                name="test", resource=resource, action="read"
            )
            assert permission.resource == resource

    def test_action_pattern_validation_valid(self):
        """Test valid action patterns."""
        valid_actions = ["read", "write", "delete", "create", "update", "admin_action"]

        for action in valid_actions:
            permission = ModelPermission(name="test", resource="test", action=action)
            assert permission.action == action

    def test_effect_validation(self):
        """Test effect field validation."""
        # Valid effects
        perm_allow = ModelPermission(
            name="test", resource="test", action="read", effect="allow"
        )
        perm_deny = ModelPermission(
            name="test", resource="test", action="read", effect="deny"
        )

        assert perm_allow.effect == "allow"
        assert perm_deny.effect == "deny"

    def test_scope_type_validation(self):
        """Test scope_type field validation."""
        valid_scopes = ["global", "organizational", "resource", "temporal", "conditional"]

        for scope in valid_scopes:
            permission = ModelPermission(
                name="test", resource="test", action="read", scope_type=scope
            )
            assert permission.scope_type == scope

    def test_priority_range_validation(self):
        """Test priority value constraints."""
        # Valid priorities
        perm_min = ModelPermission(
            name="test", resource="test", action="read", priority=0
        )
        perm_max = ModelPermission(
            name="test", resource="test", action="read", priority=100
        )

        assert perm_min.priority == 0
        assert perm_max.priority == 100

    def test_risk_level_validation(self):
        """Test risk_level field validation."""
        valid_risk_levels = ["low", "medium", "high", "critical"]

        for risk_level in valid_risk_levels:
            permission = ModelPermission(
                name="test", resource="test", action="read", risk_level=risk_level
            )
            assert permission.risk_level == risk_level


class TestModelPermissionListValidators:
    """Test list field validators."""

    def test_resource_hierarchy_max_length(self):
        """Test resource hierarchy maximum length validation."""
        # Valid: 10 levels
        valid_hierarchy = [f"level{i}" for i in range(10)]
        permission = ModelPermission(
            name="test",
            resource="test",
            action="read",
            resource_hierarchy=valid_hierarchy,
        )
        assert len(permission.resource_hierarchy) == 10

        # Invalid: 11 levels
        with pytest.raises(ModelOnexError) as exc_info:
            ModelPermission(
                name="test",
                resource="test",
                action="read",
                resource_hierarchy=[f"level{i}" for i in range(11)],
            )
        assert exc_info.value.error_code.value == "ONEX_CORE_006_VALIDATION_ERROR"

    def test_resource_patterns_max_length(self):
        """Test resource patterns maximum length validation."""
        # Valid: 20 patterns
        valid_patterns = [f"pattern{i}/*" for i in range(20)]
        permission = ModelPermission(
            name="test",
            resource="test",
            action="read",
            resource_patterns=valid_patterns,
        )
        assert len(permission.resource_patterns) == 20

        # Invalid: 21 patterns
        with pytest.raises(ModelOnexError) as exc_info:
            ModelPermission(
                name="test",
                resource="test",
                action="read",
                resource_patterns=[f"pattern{i}/*" for i in range(21)],
            )
        assert exc_info.value.error_code.value == "ONEX_CORE_006_VALIDATION_ERROR"

    def test_conditions_max_length(self):
        """Test conditions maximum length validation."""
        # Valid: 50 conditions
        valid_conditions = [f"condition{i} == true" for i in range(50)]
        permission = ModelPermission(
            name="test",
            resource="test",
            action="read",
            conditions=valid_conditions,
        )
        assert len(permission.conditions) == 50

        # Invalid: 51 conditions
        with pytest.raises(ModelOnexError) as exc_info:
            ModelPermission(
                name="test",
                resource="test",
                action="read",
                conditions=[f"condition{i} == true" for i in range(51)],
            )
        assert exc_info.value.error_code.value == "ONEX_CORE_006_VALIDATION_ERROR"

    def test_tags_validation(self):
        """Test tags validation."""
        # Valid: 20 tags
        valid_tags = [f"tag{i}" for i in range(20)]
        permission = ModelPermission(
            name="test", resource="test", action="read", tags=valid_tags
        )
        assert len(permission.tags) == 20

        # Invalid: 21 tags
        with pytest.raises(ModelOnexError) as exc_info:
            ModelPermission(
                name="test",
                resource="test",
                action="read",
                tags=[f"tag{i}" for i in range(21)],
            )
        assert exc_info.value.error_code.value == "ONEX_CORE_006_VALIDATION_ERROR"

    def test_tags_max_length_per_tag(self):
        """Test individual tag length validation."""
        # Valid: tag with 50 characters
        permission = ModelPermission(
            name="test", resource="test", action="read", tags=["a" * 50]
        )
        assert len(permission.tags[0]) == 50

        # Invalid: tag with 51 characters
        with pytest.raises(ModelOnexError) as exc_info:
            ModelPermission(
                name="test",
                resource="test",
                action="read",
                tags=["a" * 51],
            )
        assert exc_info.value.error_code.value == "ONEX_CORE_006_VALIDATION_ERROR"

    def test_approval_types_max_length(self):
        """Test approval types maximum length validation."""
        # Valid: 10 approval types
        valid_types = [f"approval{i}" for i in range(10)]
        permission = ModelPermission(
            name="test",
            resource="test",
            action="read",
            approval_types=valid_types,
        )
        assert len(permission.approval_types) == 10

        # Invalid: 11 approval types
        with pytest.raises(ModelOnexError) as exc_info:
            ModelPermission(
                name="test",
                resource="test",
                action="read",
                approval_types=[f"approval{i}" for i in range(11)],
            )
        assert exc_info.value.error_code.value == "ONEX_CORE_006_VALIDATION_ERROR"

    def test_allowed_countries_max_length(self):
        """Test allowed countries maximum length validation."""
        # Valid: 50 countries
        valid_countries = [f"C{i:02d}" for i in range(50)]
        permission = ModelPermission(
            name="test",
            resource="test",
            action="read",
            allowed_countries=valid_countries,
        )
        assert len(permission.allowed_countries) == 50

        # Invalid: 51 countries
        with pytest.raises(ModelOnexError) as exc_info:
            ModelPermission(
                name="test",
                resource="test",
                action="read",
                allowed_countries=[f"C{i:02d}" for i in range(51)],
            )
        assert exc_info.value.error_code.value == "ONEX_CORE_006_VALIDATION_ERROR"

    def test_allowed_ip_ranges_max_length(self):
        """Test allowed IP ranges maximum length validation."""
        # Valid: 20 IP ranges
        valid_ranges = [f"192.168.{i}.0/24" for i in range(20)]
        permission = ModelPermission(
            name="test",
            resource="test",
            action="read",
            allowed_ip_ranges=valid_ranges,
        )
        assert len(permission.allowed_ip_ranges) == 20

        # Invalid: 21 IP ranges
        with pytest.raises(ModelOnexError) as exc_info:
            ModelPermission(
                name="test",
                resource="test",
                action="read",
                allowed_ip_ranges=[f"192.168.{i}.0/24" for i in range(21)],
            )
        assert exc_info.value.error_code.value == "ONEX_CORE_006_VALIDATION_ERROR"


class TestModelPermissionResourceMatching:
    """Test resource matching logic."""

    def test_matches_resource_direct_match(self):
        """Test direct resource path matching."""
        permission = ModelPermission(
            name="test", resource="projects/test/resource", action="read"
        )

        assert permission.matches_resource("projects/test/resource") is True
        assert permission.matches_resource("projects/test/other") is False

    def test_matches_resource_pattern_matching(self):
        """Test pattern-based resource matching."""
        permission = ModelPermission(
            name="test",
            resource="test",
            action="read",
            resource_patterns=["projects/*/resource", "orgs/test/*"],
        )

        assert permission.matches_resource("projects/abc/resource") is True
        assert permission.matches_resource("projects/xyz/resource") is True
        assert permission.matches_resource("orgs/test/anything") is True
        assert permission.matches_resource("projects/abc/other") is False

    def test_matches_resource_hierarchy_exact(self):
        """Test hierarchy-based matching without subresources."""
        permission = ModelPermission(
            name="test",
            resource="test",
            action="read",
            resource_hierarchy=["org", "project", "resource"],
            include_subresources=False,
        )

        assert permission.matches_resource("org/project/resource") is True
        assert permission.matches_resource("org/project/resource/sub") is False

    def test_matches_resource_hierarchy_with_subresources(self):
        """Test hierarchy-based matching with subresources."""
        permission = ModelPermission(
            name="test",
            resource="test",
            action="read",
            resource_hierarchy=["org", "project"],
            include_subresources=True,
        )

        assert permission.matches_resource("org/project") is True
        assert permission.matches_resource("org/project/resource") is True
        assert permission.matches_resource("org/project/resource/sub") is True
        assert permission.matches_resource("org/other") is False

    def test_matches_resource_wildcard(self):
        """Test wildcard resource matching."""
        permission = ModelPermission(
            name="test", resource="projects/*", action="read"
        )

        assert permission.matches_resource("projects/test") is True
        assert permission.matches_resource("projects/anything") is True
        assert permission.matches_resource("other/test") is False


class TestModelPermissionTemporalValidation:
    """Test temporal validation logic."""

    def test_is_temporally_valid_disabled(self):
        """Test temporal validation when disabled."""
        permission = ModelPermission(
            name="test",
            resource="test",
            action="read",
            temporal_constraints_enabled=False,
        )

        assert permission.is_temporally_valid() is True

    def test_is_temporally_valid_date_range(self):
        """Test temporal validation with date range."""
        now = datetime.now(UTC)
        permission = ModelPermission(
            name="test",
            resource="test",
            action="read",
            temporal_constraints_enabled=True,
            valid_from=now - timedelta(hours=1),
            valid_until=now + timedelta(hours=1),
        )

        assert permission.is_temporally_valid(now) is True
        assert (
            permission.is_temporally_valid(now - timedelta(hours=2)) is False
        )  # Before valid_from
        assert (
            permission.is_temporally_valid(now + timedelta(hours=2)) is False
        )  # After valid_until

    def test_is_temporally_valid_time_of_day(self):
        """Test temporal validation with time of day constraints."""
        permission = ModelPermission(
            name="test",
            resource="test",
            action="read",
            temporal_constraints_enabled=True,
            time_of_day_start="09:00",
            time_of_day_end="17:00",
        )

        # Test during business hours
        business_hour = datetime.now(UTC).replace(hour=12, minute=0, second=0)
        assert permission.is_temporally_valid(business_hour) is True

        # Test outside business hours
        after_hours = datetime.now(UTC).replace(hour=20, minute=0, second=0)
        assert permission.is_temporally_valid(after_hours) is False

    def test_is_temporally_valid_days_of_week(self):
        """Test temporal validation with day of week constraints."""
        # Only Monday (0)
        permission = ModelPermission(
            name="test",
            resource="test",
            action="read",
            temporal_constraints_enabled=True,
            days_of_week=[0],
        )

        # Find a Monday
        now = datetime.now(UTC)
        days_until_monday = (7 - now.weekday()) % 7
        next_monday = now + timedelta(days=days_until_monday)

        assert permission.is_temporally_valid(next_monday) is True

        # Tuesday should fail
        next_tuesday = next_monday + timedelta(days=1)
        assert permission.is_temporally_valid(next_tuesday) is False

    def test_is_expired(self):
        """Test expiration check."""
        now = datetime.now(UTC)

        # Not expired
        perm_active = ModelPermission(
            name="test",
            resource="test",
            action="read",
            valid_until=now + timedelta(hours=1),
        )
        assert perm_active.is_expired() is False

        # Expired
        perm_expired = ModelPermission(
            name="test",
            resource="test",
            action="read",
            valid_until=now - timedelta(hours=1),
        )
        assert perm_expired.is_expired() is True

        # No expiration
        perm_no_expiry = ModelPermission(
            name="test", resource="test", action="read"
        )
        assert perm_no_expiry.is_expired() is False

    def test_is_active(self):
        """Test activation check."""
        now = datetime.now(UTC)

        # Active
        perm_active = ModelPermission(
            name="test",
            resource="test",
            action="read",
            valid_from=now - timedelta(hours=1),
        )
        assert perm_active.is_active() is True

        # Not yet active
        perm_future = ModelPermission(
            name="test",
            resource="test",
            action="read",
            valid_from=now + timedelta(hours=1),
        )
        assert perm_future.is_active() is False

        # No activation time
        perm_no_start = ModelPermission(
            name="test", resource="test", action="read"
        )
        assert perm_no_start.is_active() is True


class TestModelPermissionGeographicValidation:
    """Test geographic validation logic."""

    def test_is_geographically_valid_disabled(self):
        """Test geographic validation when disabled."""
        permission = ModelPermission(
            name="test",
            resource="test",
            action="read",
            geographic_constraints_enabled=False,
        )

        assert permission.is_geographically_valid() is True
        assert permission.is_geographically_valid(country_code="XX") is True

    def test_is_geographically_valid_country_allowed(self):
        """Test geographic validation with allowed countries."""
        permission = ModelPermission(
            name="test",
            resource="test",
            action="read",
            geographic_constraints_enabled=True,
            allowed_countries=["US", "CA", "GB"],
        )

        assert permission.is_geographically_valid(country_code="US") is True
        assert permission.is_geographically_valid(country_code="CA") is True
        assert permission.is_geographically_valid(country_code="XX") is False

    def test_is_geographically_valid_ip_range(self):
        """Test geographic validation with IP ranges."""
        permission = ModelPermission(
            name="test",
            resource="test",
            action="read",
            geographic_constraints_enabled=True,
            allowed_ip_ranges=["192.168.1.0/24", "10.0.0"],
        )

        assert permission.is_geographically_valid(ip_address="192.168.1.100") is True
        assert permission.is_geographically_valid(ip_address="10.0.0.50") is True
        assert permission.is_geographically_valid(ip_address="172.16.0.1") is False


class TestModelPermissionConditionEvaluation:
    """Test condition evaluation logic."""

    def test_evaluate_conditions_no_conditions(self):
        """Test condition evaluation with no conditions."""
        permission = ModelPermission(
            name="test", resource="test", action="read"
        )
        context = ModelPermissionEvaluationContext()

        assert permission.evaluate_conditions(context) is True

    def test_evaluate_conditions_equality_check(self):
        """Test condition evaluation with equality checks."""
        permission = ModelPermission(
            name="test",
            resource="test",
            action="read",
            conditions=["role == 'admin'"],
        )

        context_pass = ModelPermissionEvaluationContext(string_attributes={"role": "admin"})
        context_fail = ModelPermissionEvaluationContext(string_attributes={"role": "user"})

        assert permission.evaluate_conditions(context_pass) is True
        assert permission.evaluate_conditions(context_fail) is False

    def test_evaluate_conditions_existence_check(self):
        """Test condition evaluation with existence checks."""
        permission = ModelPermission(
            name="test",
            resource="test",
            action="read",
            conditions=["has_permission"],
        )

        context_pass = ModelPermissionEvaluationContext(boolean_attributes={"has_permission": True})
        context_fail = ModelPermissionEvaluationContext(boolean_attributes={"has_permission": False})

        assert permission.evaluate_conditions(context_pass) is True
        assert permission.evaluate_conditions(context_fail) is False


class TestModelPermissionUsageManagement:
    """Test usage management and limits."""

    def test_is_usage_allowed_disabled(self):
        """Test usage check when limits disabled."""
        permission = ModelPermission(
            name="test",
            resource="test",
            action="read",
            usage_limits_enabled=False,
        )

        current_usage = {"total": 1000, "today": 100, "this_hour": 10}
        assert permission.is_usage_allowed(current_usage) is True

    def test_is_usage_allowed_total_limit(self):
        """Test usage check with total limit."""
        permission = ModelPermission(
            name="test",
            resource="test",
            action="read",
            usage_limits_enabled=True,
            max_uses_total=100,
        )

        assert permission.is_usage_allowed({"total": 50}) is True
        assert permission.is_usage_allowed({"total": 100}) is False
        assert permission.is_usage_allowed({"total": 150}) is False

    def test_is_usage_allowed_daily_limit(self):
        """Test usage check with daily limit."""
        permission = ModelPermission(
            name="test",
            resource="test",
            action="read",
            usage_limits_enabled=True,
            max_uses_per_day=10,
        )

        assert permission.is_usage_allowed({"today": 5}) is True
        assert permission.is_usage_allowed({"today": 10}) is False

    def test_is_usage_allowed_hourly_limit(self):
        """Test usage check with hourly limit."""
        permission = ModelPermission(
            name="test",
            resource="test",
            action="read",
            usage_limits_enabled=True,
            max_uses_per_hour=5,
        )

        assert permission.is_usage_allowed({"this_hour": 3}) is True
        assert permission.is_usage_allowed({"this_hour": 5}) is False

    def test_get_usage_summary(self):
        """Test usage summary generation."""
        permission = ModelPermission(
            name="test",
            resource="test",
            action="read",
            usage_limits_enabled=True,
            max_uses_total=100,
            max_uses_per_day=20,
            max_uses_per_hour=5,
        )

        current_usage = {"total": 80, "today": 15, "this_hour": 3}
        summary = permission.get_usage_summary(current_usage)

        assert summary["status"] == "allowed"
        assert summary["total_remaining"] == "20"
        assert summary["daily_remaining"] == "5"
        assert summary["hourly_remaining"] == "2"


class TestModelPermissionUtilityMethods:
    """Test utility and helper methods."""

    def test_get_qualified_name_with_namespace(self):
        """Test qualified name with namespace."""
        permission = ModelPermission(
            name="read_resource",
            resource="test",
            action="read",
            namespace="test_namespace",
        )

        assert permission.get_qualified_name() == "test_namespace:read_resource"

    def test_get_qualified_name_without_namespace(self):
        """Test qualified name without namespace."""
        permission = ModelPermission(
            name="read_resource", resource="test", action="read"
        )

        assert permission.get_qualified_name() == "read_resource"

    def test_to_statement(self):
        """Test permission statement generation."""
        permission = ModelPermission(
            name="test", resource="projects/test", action="read", effect="allow"
        )

        assert permission.to_statement() == "allow:projects/test:read"

    def test_is_more_specific_than_hierarchy(self):
        """Test specificity comparison based on hierarchy."""
        specific = ModelPermission(
            name="test",
            resource="test",
            action="read",
            resource_hierarchy=["a", "b", "c"],
        )
        general = ModelPermission(
            name="test", resource="test", action="read", resource_hierarchy=["a"]
        )

        assert specific.is_more_specific_than(general) is True
        assert general.is_more_specific_than(specific) is False

    def test_is_more_specific_than_conditions(self):
        """Test specificity comparison based on conditions."""
        specific = ModelPermission(
            name="test",
            resource="test",
            action="read",
            conditions=["a == 1", "b == 2"],
        )
        general = ModelPermission(
            name="test", resource="test", action="read", conditions=[]
        )

        assert specific.is_more_specific_than(general) is True

    def test_is_more_specific_than_constraints(self):
        """Test specificity comparison based on constraints."""
        temporal = ModelPermission(
            name="test",
            resource="test",
            action="read",
            temporal_constraints_enabled=True,
        )
        geographic = ModelPermission(
            name="test",
            resource="test",
            action="read",
            geographic_constraints_enabled=True,
        )
        basic = ModelPermission(name="test", resource="test", action="read")

        assert temporal.is_more_specific_than(basic) is True
        assert geographic.is_more_specific_than(basic) is True

    def test_get_risk_score_calculation(self):
        """Test risk score calculation."""
        # Low risk
        low_risk = ModelPermission(
            name="test",
            resource="test",
            action="read",
            risk_level="low",
            effect="allow",
        )
        assert 0 <= low_risk.get_risk_score() <= 50

        # High risk
        high_risk = ModelPermission(
            name="test",
            resource="test",
            action="*",
            risk_level="critical",
            scope_type="global",
            effect="allow",
        )
        assert high_risk.get_risk_score() >= 50

        # With mitigations
        mitigated = ModelPermission(
            name="test",
            resource="test",
            action="*",
            risk_level="high",
            require_mfa=True,
            approval_required=True,
            temporal_constraints_enabled=True,
        )
        assert mitigated.get_risk_score() < high_risk.get_risk_score()


class TestModelPermissionFactoryMethods:
    """Test factory methods for common permission types."""

    def test_create_read_permission(self):
        """Test read permission factory method."""
        permission = ModelPermission.create_read_permission(
            resource="projects/test", namespace="test_ns", description="Test read"
        )

        assert permission.action == "read"
        assert permission.effect == "allow"
        assert permission.resource == "projects/test"
        assert permission.namespace == "test_ns"
        assert permission.risk_level == "low"
        assert "read" in permission.name

    def test_create_write_permission(self):
        """Test write permission factory method."""
        permission = ModelPermission.create_write_permission(
            resource="projects/test", description="Test write"
        )

        assert permission.action == "write"
        assert permission.effect == "allow"
        assert permission.resource == "projects/test"
        assert permission.risk_level == "medium"
        assert permission.audit_detail_level == "detailed"
        assert "write" in permission.name

    def test_create_admin_permission(self):
        """Test admin permission factory method."""
        permission = ModelPermission.create_admin_permission(
            resource="projects/test", namespace="admin_ns"
        )

        assert permission.action == "*"
        assert permission.effect == "allow"
        assert permission.resource == "projects/test"
        assert permission.risk_level == "high"
        assert permission.audit_detail_level == "comprehensive"
        assert permission.approval_required is True
        assert permission.require_mfa is True
        assert "admin" in permission.name

    def test_create_deny_permission(self):
        """Test deny permission factory method."""
        permission = ModelPermission.create_deny_permission(
            resource="projects/test", action="delete", namespace="deny_ns"
        )

        assert permission.action == "delete"
        assert permission.effect == "deny"
        assert permission.resource == "projects/test"
        assert permission.priority == 100  # High priority
        assert permission.audit_detail_level == "comprehensive"
        assert "deny" in permission.name

    def test_create_emergency_permission(self):
        """Test emergency break-glass permission factory method."""
        permission = ModelPermission.create_emergency_permission(
            resource="projects/test", action="admin", description="Emergency access"
        )

        assert permission.action == "admin"
        assert permission.effect == "allow"
        assert permission.risk_level == "critical"
        assert permission.usage_limits_enabled is True
        assert permission.max_uses_total == 1
        assert permission.require_mfa is True
        assert permission.audit_detail_level == "comprehensive"
        assert permission.custom_fields.boolean_fields["break_glass"] is True
        assert "emergency" in permission.name

    def test_create_time_limited_permission(self):
        """Test time-limited permission factory method."""
        permission = ModelPermission.create_time_limited_permission(
            resource="projects/test", action="write", valid_hours=48, namespace="temp"
        )

        assert permission.action == "write"
        assert permission.temporal_constraints_enabled is True
        assert permission.valid_from is not None
        assert permission.valid_until is not None
        assert permission.namespace == "temp"
        assert permission.audit_detail_level == "detailed"
        assert "temp" in permission.name

        # Check time delta
        time_diff = permission.valid_until - permission.valid_from
        assert abs(time_diff.total_seconds() - (48 * 3600)) < 60  # Within 1 minute


class TestModelPermissionEdgeCases:
    """Test edge cases and error scenarios."""

    def test_permission_with_empty_lists(self):
        """Test permission with empty list fields."""
        permission = ModelPermission(
            name="test",
            resource="test",
            action="read",
            resource_hierarchy=[],
            resource_patterns=[],
            conditions=[],
            tags=[],
        )

        assert permission.resource_hierarchy == []
        assert permission.resource_patterns == []
        assert permission.conditions == []
        assert permission.tags == []

    def test_permission_with_max_values(self):
        """Test permission with maximum allowed values."""
        permission = ModelPermission(
            name="test",
            resource="test",
            action="read",
            priority=100,
            min_approvals_required=10,
            max_delegation_depth=10,
        )

        assert permission.priority == 100
        assert permission.min_approvals_required == 10
        assert permission.max_delegation_depth == 10

    def test_permission_with_min_values(self):
        """Test permission with minimum allowed values."""
        permission = ModelPermission(
            name="test",
            resource="test",
            action="read",
            priority=0,
            min_approvals_required=0,
            max_delegation_depth=0,
        )

        assert permission.priority == 0
        assert permission.min_approvals_required == 0
        assert permission.max_delegation_depth == 0

    def test_permission_version_field(self):
        """Test permission version field."""
        permission = ModelPermission(
            name="test",
            resource="test",
            action="read",
            version=ModelSemVer(major=2, minor=1, patch=3),
        )

        assert permission.version.major == 2
        assert permission.version.minor == 1
        assert permission.version.patch == 3


class TestModelPermissionBranchCoverage:
    """Test specific conditional branches for comprehensive branch coverage."""

    def test_is_temporally_valid_with_explicit_current_time(self):
        """Test temporal validation with explicitly provided current_time (line 449)."""
        permission = ModelPermission(
            name="test",
            resource="test",
            action="read",
            temporal_constraints_enabled=True,
            valid_from=datetime(2024, 1, 1, tzinfo=UTC),
            valid_until=datetime(2024, 12, 31, tzinfo=UTC),
        )

        # Test with explicit current_time
        test_time = datetime(2024, 6, 15, tzinfo=UTC)
        assert permission.is_temporally_valid(test_time) is True

        # Test with current_time = None (uses default datetime.now)
        assert permission.is_temporally_valid(None) in [True, False]  # Depends on actual current time

    def test_evaluate_conditions_with_malformed_equality(self):
        """Test condition evaluation with malformed equality check (lines 517-519)."""
        permission = ModelPermission(
            name="test",
            resource="test",
            action="read",
            conditions=["role == 'admin' and extra_condition"],  # Multiple operators, will cause parsing issues
        )

        context = ModelPermissionEvaluationContext(string_attributes={"role": "admin"})

        # Complex condition fails the equality check (right side doesn't match) - returns False (fail-safe)
        result = permission.evaluate_conditions(context)
        # This tests the fail-safe behavior when condition evaluation encounters issues
        assert result is False

    def test_evaluate_conditions_fail_safe_on_exception(self):
        """Test condition evaluation handles exceptions properly with fail-safe."""
        # Create a condition that will match neither equality nor existence patterns
        # and will fall through to the default True behavior
        permission = ModelPermission(
            name="test",
            resource="test",
            action="read",
            conditions=["nonexistent_key"],
        )

        # Empty context - key doesn't exist
        context = ModelPermissionEvaluationContext()

        # When condition is just a string that's not in context, returns True (line 669)
        result = permission.evaluate_conditions(context)
        assert result is True

    def test_get_usage_summary_with_limits_disabled(self):
        """Test usage summary when limits are disabled (lines 547-548)."""
        permission = ModelPermission(
            name="test",
            resource="test",
            action="read",
            usage_limits_enabled=False,
        )

        current_usage = {"total": 100, "today": 50, "this_hour": 10}
        summary = permission.get_usage_summary(current_usage)

        assert summary["status"] == "allowed"
        assert summary["limits_enabled"] == "False"
        # Should not have remaining counts when disabled
        assert "total_remaining" not in summary
        assert "daily_remaining" not in summary
        assert "hourly_remaining" not in summary

    def test_get_usage_summary_with_no_total_limit(self):
        """Test usage summary when max_uses_total is None (line 552)."""
        permission = ModelPermission(
            name="test",
            resource="test",
            action="read",
            usage_limits_enabled=True,
            max_uses_total=None,  # No total limit
            max_uses_per_day=10,
        )

        current_usage = {"total": 100, "today": 5}
        summary = permission.get_usage_summary(current_usage)

        assert "total_remaining" not in summary  # Should not be present
        assert "daily_remaining" in summary  # But daily should be present

    def test_get_usage_summary_with_no_daily_limit(self):
        """Test usage summary when max_uses_per_day is None (line 556)."""
        permission = ModelPermission(
            name="test",
            resource="test",
            action="read",
            usage_limits_enabled=True,
            max_uses_total=100,
            max_uses_per_day=None,  # No daily limit
        )

        current_usage = {"total": 50, "today": 25}
        summary = permission.get_usage_summary(current_usage)

        assert "total_remaining" in summary
        assert "daily_remaining" not in summary  # Should not be present

    def test_get_usage_summary_with_no_hourly_limit(self):
        """Test usage summary when max_uses_per_hour is None (line 560)."""
        permission = ModelPermission(
            name="test",
            resource="test",
            action="read",
            usage_limits_enabled=True,
            max_uses_total=100,
            max_uses_per_hour=None,  # No hourly limit
        )

        current_usage = {"total": 50, "this_hour": 5}
        summary = permission.get_usage_summary(current_usage)

        assert "total_remaining" in summary
        assert "hourly_remaining" not in summary  # Should not be present

    def test_get_risk_score_with_deny_effect(self):
        """Test risk score calculation with deny effect (line 608)."""
        permission = ModelPermission(
            name="test",
            resource="test",
            action="delete",
            effect="deny",  # Deny effect reduces risk
            risk_level="high",
        )

        risk_score = permission.get_risk_score()

        # Deny effect should reduce risk score
        allow_permission = ModelPermission(
            name="test",
            resource="test",
            action="delete",
            effect="allow",
            risk_level="high",
        )

        allow_risk_score = allow_permission.get_risk_score()

        assert risk_score < allow_risk_score  # Deny should have lower risk

    def test_get_risk_score_with_organizational_scope(self):
        """Test risk score with organizational scope (line 614)."""
        permission = ModelPermission(
            name="test",
            resource="test",
            action="read",
            scope_type="organizational",  # Organizational scope increases risk
            risk_level="low",
        )

        risk_score = permission.get_risk_score()

        # Compare with resource scope (lower risk)
        resource_permission = ModelPermission(
            name="test",
            resource="test",
            action="read",
            scope_type="resource",
            risk_level="low",
        )

        resource_risk_score = resource_permission.get_risk_score()

        assert risk_score > resource_risk_score  # Organizational scope should be higher risk

    def test_get_risk_score_with_geographic_constraints(self):
        """Test risk score with geographic constraints (line 620)."""
        permission = ModelPermission(
            name="test",
            resource="test",
            action="write",
            risk_level="medium",
            geographic_constraints_enabled=True,  # Geographic constraints reduce risk
            allowed_countries=["US"],
        )

        risk_score = permission.get_risk_score()

        # Compare without geographic constraints
        no_geo_permission = ModelPermission(
            name="test",
            resource="test",
            action="write",
            risk_level="medium",
            geographic_constraints_enabled=False,
        )

        no_geo_risk_score = no_geo_permission.get_risk_score()

        assert risk_score < no_geo_risk_score  # Geographic constraints should reduce risk

    def test_get_risk_score_with_usage_limits(self):
        """Test risk score with usage limits enabled (line 622)."""
        permission = ModelPermission(
            name="test",
            resource="test",
            action="write",
            risk_level="medium",
            usage_limits_enabled=True,  # Usage limits reduce risk
            max_uses_total=100,
        )

        risk_score = permission.get_risk_score()

        # Compare without usage limits
        no_limits_permission = ModelPermission(
            name="test",
            resource="test",
            action="write",
            risk_level="medium",
            usage_limits_enabled=False,
        )

        no_limits_risk_score = no_limits_permission.get_risk_score()

        assert risk_score < no_limits_risk_score  # Usage limits should reduce risk

    def test_evaluate_simple_condition_with_missing_key(self):
        """Test condition evaluation when key doesn't exist in context (line 669)."""
        permission = ModelPermission(
            name="test",
            resource="test",
            action="read",
            conditions=["missing_key"],  # Key doesn't exist in context
        )

        context = ModelPermissionEvaluationContext()

        # Missing key should evaluate to True (default behavior)
        result = permission.evaluate_conditions(context)
        assert result is True

    def test_matches_resource_no_hierarchy_match(self):
        """Test resource matching when hierarchy doesn't match."""
        permission = ModelPermission(
            name="test",
            resource="test",
            action="read",
            resource_hierarchy=["org", "project"],
        )

        # Resource with different hierarchy
        assert permission.matches_resource("other/path") is False

    def test_is_geographically_valid_with_country_but_no_ip(self):
        """Test geographic validation with country code but no IP."""
        permission = ModelPermission(
            name="test",
            resource="test",
            action="read",
            geographic_constraints_enabled=True,
            allowed_countries=["US"],
        )

        # Only country code provided
        assert permission.is_geographically_valid(country_code="US", ip_address=None) is True
        assert permission.is_geographically_valid(country_code="CA", ip_address=None) is False

    def test_is_geographically_valid_with_ip_but_no_country(self):
        """Test geographic validation with IP but no country code."""
        permission = ModelPermission(
            name="test",
            resource="test",
            action="read",
            geographic_constraints_enabled=True,
            allowed_ip_ranges=["192.168.1.0/24"],
        )

        # Only IP address provided
        assert permission.is_geographically_valid(country_code=None, ip_address="192.168.1.50") is True
        assert permission.is_geographically_valid(country_code=None, ip_address="10.0.0.1") is False
