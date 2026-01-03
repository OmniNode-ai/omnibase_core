"""
ModelPermissionScope - Permission scope configuration

Permission scope model for defining the context and boundaries of permissions
including resource hierarchies, temporal constraints, and geographic limitations.
"""

import fnmatch
from datetime import UTC, datetime
from uuid import UUID, uuid4

from pydantic import BaseModel, Field

from omnibase_core.models.security.model_context_variables import ModelContextVariables
from omnibase_core.models.security.model_permission_evaluation_context import (
    ModelPermissionEvaluationContext,
)
from omnibase_core.models.security.model_permission_metadata import (
    ModelPermissionMetadata,
)
from omnibase_core.types.type_serializable_value import SerializedDict


class ModelPermissionScope(BaseModel):
    """
    Permission scope configuration model

    This model defines the boundaries and context within which a permission
    is valid, including resource hierarchies, time constraints, and conditions.
    """

    scope_id: UUID = Field(
        default=...,
        description="Unique scope identifier",
        pattern="^[a-z][a-z0-9_-]*$",
    )

    scope_type: str = Field(
        default="resource",
        description="Type of permission scope",
        pattern="^(resource|organizational|temporal|geographic|conditional)$",
    )

    resource_hierarchy: list[str] = Field(
        default_factory=list,
        description="Resource hierarchy path (e.g., ['organization', 'project', 'resource'])",
    )

    organizational_units: list[str] = Field(
        default_factory=list,
        description="Organizational units within scope",
    )

    resource_types: list[str] = Field(
        default_factory=list,
        description="Types of resources covered by this scope",
    )

    resource_patterns: list[str] = Field(
        default_factory=list,
        description="Resource name patterns (glob or regex patterns)",
    )

    include_subresources: bool = Field(
        default=True,
        description="Whether permission applies to subresources",
    )

    temporal_constraints_enabled: bool = Field(
        default=False,
        description="Whether temporal constraints are enabled",
    )

    valid_from: datetime | None = Field(
        default=None,
        description="Permission valid from this timestamp",
    )

    valid_until: datetime | None = Field(
        default=None,
        description="Permission valid until this timestamp",
    )

    time_of_day_start: str | None = Field(
        default=None,
        description="Daily validity start time (HH:MM format)",
        pattern="^([01]?[0-9]|2[0-3]):[0-5][0-9]$",
    )

    time_of_day_end: str | None = Field(
        default=None,
        description="Daily validity end time (HH:MM format)",
        pattern="^([01]?[0-9]|2[0-3]):[0-5][0-9]$",
    )

    days_of_week: list[int] = Field(
        default_factory=lambda: list(range(7)),  # All days by default
        description="Days of week when permission is valid (0=Monday, 6=Sunday)",
    )

    geographic_constraints_enabled: bool = Field(
        default=False,
        description="Whether geographic constraints are enabled",
    )

    allowed_countries: list[str] = Field(
        default_factory=list,
        description="ISO country codes where permission is valid",
    )

    allowed_regions: list[str] = Field(
        default_factory=list,
        description="Geographic regions where permission is valid",
    )

    allowed_ip_ranges: list[str] = Field(
        default_factory=list,
        description="IP address ranges (CIDR notation) where permission is valid",
    )

    conditional_expressions: list[str] = Field(
        default_factory=list,
        description="Conditional expressions that must evaluate to true",
    )

    context_variables: ModelContextVariables = Field(
        default_factory=lambda: ModelContextVariables(),
        description="Context variables available for conditional evaluation",
    )

    metadata: ModelPermissionMetadata = Field(
        default_factory=lambda: ModelPermissionMetadata(),
        description="Additional scope metadata",
    )

    def matches_resource(self, resource_path: str) -> bool:
        """Check if a resource path matches this scope"""
        if not self.resource_hierarchy and not self.resource_patterns:
            return True  # No constraints means all resources

        # Check hierarchy matching
        if self.resource_hierarchy:
            resource_parts = resource_path.split("/")
            hierarchy_matches = True

            for i, hierarchy_part in enumerate(self.resource_hierarchy):
                if i >= len(resource_parts) or not self._matches_pattern(
                    resource_parts[i],
                    hierarchy_part,
                ):
                    hierarchy_matches = False
                    break

            if hierarchy_matches:
                # If include_subresources is True, allow longer paths
                if self.include_subresources or len(resource_parts) == len(
                    self.resource_hierarchy,
                ):
                    return True

        # Check pattern matching
        if self.resource_patterns:
            import fnmatch

            for pattern in self.resource_patterns:
                if fnmatch.fnmatch(resource_path, pattern):
                    return True

        return False

    def is_temporally_valid(self, current_time: datetime | None = None) -> bool:
        """Check if permission is temporally valid"""
        if not self.temporal_constraints_enabled:
            return True

        if current_time is None:
            current_time = datetime.now(UTC)

        # Check date range
        if self.valid_from and current_time < self.valid_from:
            return False
        if self.valid_until and current_time > self.valid_until:
            return False

        # Check time of day
        if self.time_of_day_start and self.time_of_day_end:
            current_time_str = current_time.strftime("%H:%M")
            if not (self.time_of_day_start <= current_time_str <= self.time_of_day_end):
                return False

        # Check day of week (0=Monday, 6=Sunday)
        current_day = current_time.weekday()
        return current_day in self.days_of_week

    def is_geographically_valid(
        self,
        country_code: str | None = None,
        region: str | None = None,
        ip_address: str | None = None,
    ) -> bool:
        """Check if permission is geographically valid"""
        if not self.geographic_constraints_enabled:
            return True

        # Check country
        if self.allowed_countries and country_code:
            if country_code not in self.allowed_countries:
                return False

        # Check region
        if self.allowed_regions and region:
            if region not in self.allowed_regions:
                return False

        # Check IP ranges (simplified implementation)
        if self.allowed_ip_ranges and ip_address:
            # In production, would use proper CIDR matching
            ip_matches = any(
                ip_address.startswith(ip_range.split("/")[0])
                for ip_range in self.allowed_ip_ranges
            )
            if not ip_matches:
                return False

        return True

    def evaluate_conditions(self, context: ModelPermissionEvaluationContext) -> bool:
        """Evaluate conditional expressions with given context"""
        if not self.conditional_expressions:
            return True

        # Merge scope context with provided context
        # Type-safe merge: all values are str | int | bool which are valid JsonType
        full_context: SerializedDict = {}
        full_context.update(self.context_variables.string_variables)
        full_context.update(self.context_variables.integer_variables)
        full_context.update(self.context_variables.boolean_variables)
        full_context.update(context.string_attributes)
        full_context.update(context.integer_attributes)
        full_context.update(context.boolean_attributes)

        # Simple expression evaluation (in production would use safe eval)
        for expression in self.conditional_expressions:
            try:
                # Very basic evaluation - in production use ast.literal_eval or similar
                if not self._evaluate_simple_expression(expression, full_context):
                    return False
            except (
                Exception
            ):  # fallback-ok: expression evaluation fails safe, returns False on error
                return False  # Fail safe on evaluation errors

        return True

    def _matches_pattern(self, value: str, pattern: str) -> bool:
        """Check if value matches pattern (supports wildcards)"""

        return fnmatch.fnmatch(value, pattern)

    def _evaluate_simple_expression(
        self, expression: str, context: SerializedDict
    ) -> bool:
        """Simple expression evaluation (placeholder for production logic)"""
        # This is a simplified implementation
        # In production, would use a proper expression evaluator

        # Handle simple equality checks
        if "==" in expression:
            left, right = expression.split("==", 1)
            left_val = context.get(left.strip())
            right_val = right.strip().strip("'\"")
            return str(left_val) == right_val

        # Handle simple existence checks
        if expression.strip() in context:
            return bool(context[expression.strip()])

        return True  # Default to true for unknown expressions

    def get_resource_scope_breadth(self) -> int:
        """Calculate breadth of resource scope (for permission ordering)"""
        breadth = 0

        if not self.resource_hierarchy and not self.resource_patterns:
            breadth += 1000  # Global scope
        else:
            breadth += len(self.resource_patterns) * 100
            breadth += (
                (10 - len(self.resource_hierarchy)) * 10
                if self.resource_hierarchy
                else 500
            )

        if self.include_subresources:
            breadth += 200

        return breadth

    def is_more_restrictive_than(self, other: "ModelPermissionScope") -> bool:
        """Check if this scope is more restrictive than another"""
        # More hierarchy levels = more restrictive
        if len(self.resource_hierarchy) > len(other.resource_hierarchy):
            return True

        # More patterns = more restrictive
        if len(self.resource_patterns) > len(other.resource_patterns):
            return True

        # Temporal constraints = more restrictive
        if self.temporal_constraints_enabled and not other.temporal_constraints_enabled:
            return True

        # Geographic constraints = more restrictive
        if (
            self.geographic_constraints_enabled
            and not other.geographic_constraints_enabled
        ):
            return True

        # Conditional expressions = more restrictive
        return len(self.conditional_expressions) > len(other.conditional_expressions)

    @classmethod
    def create_global_scope(cls) -> "ModelPermissionScope":
        """Create global permission scope (no restrictions)"""
        return cls(scope_id=uuid4(), scope_type="resource", include_subresources=True)

    @classmethod
    def create_organizational_scope(
        cls,
        org_units: list[str],
    ) -> "ModelPermissionScope":
        """Create organizational permission scope"""
        return cls(
            scope_id=uuid4(),
            scope_type="organizational",
            organizational_units=org_units,
            include_subresources=True,
        )

    @classmethod
    def create_resource_scope(
        cls,
        resource_hierarchy: list[str],
    ) -> "ModelPermissionScope":
        """Create resource-specific permission scope"""
        return cls(
            scope_id=uuid4(),
            scope_type="resource",
            resource_hierarchy=resource_hierarchy,
            include_subresources=True,
        )

    @classmethod
    def create_temporal_scope(
        cls,
        valid_from: datetime,
        valid_until: datetime,
    ) -> "ModelPermissionScope":
        """Create temporal permission scope"""
        return cls(
            scope_id=uuid4(),
            scope_type="temporal",
            temporal_constraints_enabled=True,
            valid_from=valid_from,
            valid_until=valid_until,
        )

    @classmethod
    def create_business_hours_scope(
        cls,
        start_time: str = "09:00",
        end_time: str = "17:00",
    ) -> "ModelPermissionScope":
        """Create business hours permission scope"""
        return cls(
            scope_id=uuid4(),
            scope_type="temporal",
            temporal_constraints_enabled=True,
            time_of_day_start=start_time,
            time_of_day_end=end_time,
            days_of_week=[0, 1, 2, 3, 4],  # Monday to Friday
        )
