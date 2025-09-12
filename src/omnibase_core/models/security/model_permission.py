"""
ModelPermission - Extensible permission model

Core permission model for defining fine-grained access control with support for
resource hierarchies, actions, effects, scopes, and comprehensive constraints.
"""

from datetime import datetime
from uuid import UUID, uuid4

from pydantic import BaseModel, Field

from omnibase_core.models.security.model_permission_custom_fields import (
    ModelPermissionCustomFields,
)
from omnibase_core.models.security.model_permission_evaluation_context import (
    ModelPermissionEvaluationContext,
)
from omnibase_core.models.security.model_permission_metadata import (
    ModelPermissionMetadata,
)


class ModelPermission(BaseModel):
    """
    Extensible permission model for fine-grained access control

    This model replaces hardcoded permission enums with a flexible, extensible
    system that supports resource hierarchies, conditional access, and enterprise
    features like delegation, approval workflows, and audit trails.
    """

    permission_id: UUID = Field(
        default_factory=uuid4,
        description="Unique permission identifier",
    )

    name: str = Field(
        ...,
        description="Human-readable permission name",
        pattern="^[a-zA-Z][a-zA-Z0-9_\\-\\s]*$",
    )

    resource: str = Field(
        ...,
        description="Resource identifier or pattern",
        pattern="^[a-z][a-z0-9:._\\-/*]*$",
    )

    action: str = Field(
        ...,
        description="Action on resource",
        pattern="^[a-z][a-z0-9_]*$",
    )

    effect: str = Field(
        default="allow",
        description="Permission effect",
        pattern="^(allow|deny)$",
    )

    scope_type: str = Field(
        default="resource",
        description="Type of permission scope",
        pattern="^(global|organizational|resource|temporal|conditional)$",
    )

    resource_hierarchy: list[str] = Field(
        default_factory=list,
        description="Resource hierarchy path (e.g., ['org', 'project', 'resource'])",
    )

    resource_patterns: list[str] = Field(
        default_factory=list,
        description="Resource patterns (glob or regex)",
    )

    include_subresources: bool = Field(
        default=True,
        description="Whether permission applies to subresources",
    )

    conditions: list[str] = Field(
        default_factory=list,
        description="Conditional expressions that must be true",
    )

    priority: int = Field(
        default=0,
        description="Permission priority for conflict resolution",
        ge=0,
        le=100,
    )

    namespace: str | None = Field(
        None,
        description="Permission namespace for third-party isolation",
        pattern="^[a-z][a-z0-9_-]*$",
    )

    version: str = Field(
        default="1.0.0",
        description="Permission definition version",
        pattern="^\\d+\\.\\d+\\.\\d+$",
    )

    # Usage and constraints
    usage_limits_enabled: bool = Field(
        default=False,
        description="Whether usage limits are enforced",
    )

    max_uses_total: int | None = Field(None, description="Maximum total uses", ge=0)

    max_uses_per_day: int | None = Field(
        None,
        description="Maximum uses per day",
        ge=0,
    )

    max_uses_per_hour: int | None = Field(
        None,
        description="Maximum uses per hour",
        ge=0,
    )

    # Approval and delegation
    approval_required: bool = Field(
        default=False,
        description="Whether approval is required",
    )

    approval_types: list[str] = Field(
        default_factory=list,
        description="Types of approval required",
    )

    min_approvals_required: int = Field(
        default=1,
        description="Minimum approvals needed",
        ge=0,
    )

    delegation_allowed: bool = Field(
        default=False,
        description="Whether permission can be delegated",
    )

    max_delegation_depth: int = Field(
        default=1,
        description="Maximum delegation depth",
        ge=0,
        le=10,
    )

    # Temporal constraints
    temporal_constraints_enabled: bool = Field(
        default=False,
        description="Whether temporal constraints are active",
    )

    valid_from: datetime | None = Field(
        None,
        description="Permission valid from timestamp",
    )

    valid_until: datetime | None = Field(
        None,
        description="Permission valid until timestamp",
    )

    time_of_day_start: str | None = Field(
        None,
        description="Daily start time (HH:MM)",
        pattern="^([01]?[0-9]|2[0-3]):[0-5][0-9]$",
    )

    time_of_day_end: str | None = Field(
        None,
        description="Daily end time (HH:MM)",
        pattern="^([01]?[0-9]|2[0-3]):[0-5][0-9]$",
    )

    days_of_week: list[int] = Field(
        default_factory=lambda: list(range(7)),
        description="Valid days of week (0=Monday)",
    )

    # Geographic constraints
    geographic_constraints_enabled: bool = Field(
        default=False,
        description="Whether geographic constraints are active",
    )

    allowed_countries: list[str] = Field(
        default_factory=list,
        description="Allowed ISO country codes",
    )

    allowed_ip_ranges: list[str] = Field(
        default_factory=list,
        description="Allowed IP ranges (CIDR notation)",
    )

    # Security and audit
    risk_level: str = Field(
        default="medium",
        description="Risk level of this permission",
        pattern="^(low|medium|high|critical)$",
    )

    audit_logging_enabled: bool = Field(
        default=True,
        description="Whether audit logging is enabled",
    )

    audit_detail_level: str = Field(
        default="standard",
        description="Audit detail level",
        pattern="^(minimal|standard|detailed|comprehensive)$",
    )

    require_mfa: bool = Field(default=False, description="Whether MFA is required")

    require_secure_connection: bool = Field(
        default=False,
        description="Whether secure connection is required",
    )

    # Metadata and extensions
    description: str | None = Field(None, description="Human-readable description")

    tags: list[str] = Field(
        default_factory=list,
        description="Permission tags for organization",
    )

    compliance_tags: list[str] = Field(
        default_factory=list,
        description="Compliance framework tags",
    )

    custom_fields: ModelPermissionCustomFields = Field(
        default_factory=ModelPermissionCustomFields,
        description="Custom extension fields",
    )

    created_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="Creation timestamp",
    )

    created_by: str | None = Field(None, description="Creator identifier")

    updated_at: datetime | None = Field(None, description="Last update timestamp")

    updated_by: str | None = Field(None, description="Last updater identifier")

    metadata: ModelPermissionMetadata = Field(
        default_factory=ModelPermissionMetadata,
        description="Additional metadata",
    )

    def matches_resource(self, resource_path: str) -> bool:
        """Check if permission matches a resource path"""
        # Direct match
        if self.resource == resource_path:
            return True

        # Pattern matching
        if self.resource_patterns:
            import fnmatch

            for pattern in self.resource_patterns:
                if fnmatch.fnmatch(resource_path, pattern):
                    return True

        # Hierarchy matching
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
                if self.include_subresources or len(resource_parts) == len(
                    self.resource_hierarchy,
                ):
                    return True

        # Wildcard matching
        if "*" in self.resource:
            import fnmatch

            return fnmatch.fnmatch(resource_path, self.resource)

        return False

    def is_temporally_valid(self, current_time: datetime | None = None) -> bool:
        """Check if permission is temporally valid"""
        if not self.temporal_constraints_enabled:
            return True

        if current_time is None:
            current_time = datetime.utcnow()

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

        # Check day of week
        current_day = current_time.weekday()
        return current_day in self.days_of_week

    def is_geographically_valid(
        self,
        country_code: str | None = None,
        ip_address: str | None = None,
    ) -> bool:
        """Check if permission is geographically valid"""
        if not self.geographic_constraints_enabled:
            return True

        # Check country
        if self.allowed_countries and country_code:
            if country_code not in self.allowed_countries:
                return False

        # Check IP ranges
        if self.allowed_ip_ranges and ip_address:
            ip_matches = any(
                self._ip_in_cidr(ip_address, ip_range)
                for ip_range in self.allowed_ip_ranges
            )
            if not ip_matches:
                return False

        return True

    def evaluate_conditions(self, context: ModelPermissionEvaluationContext) -> bool:
        """Evaluate conditional expressions"""
        if not self.conditions:
            return True

        for condition in self.conditions:
            try:
                if not self._evaluate_simple_condition(condition, context):
                    return False
            except Exception:
                return False  # Fail safe

        return True

    def is_usage_allowed(self, current_usage: dict[str, int]) -> bool:
        """Check if usage limits allow access"""
        if not self.usage_limits_enabled:
            return True

        if self.max_uses_total and current_usage.get("total", 0) >= self.max_uses_total:
            return False

        if (
            self.max_uses_per_day
            and current_usage.get("today", 0) >= self.max_uses_per_day
        ):
            return False

        return not (
            self.max_uses_per_hour
            and current_usage.get("this_hour", 0) >= self.max_uses_per_hour
        )

    def get_qualified_name(self) -> str:
        """Get qualified permission name with namespace"""
        if self.namespace:
            return f"{self.namespace}:{self.name}"
        return self.name

    def to_statement(self) -> str:
        """Convert to permission statement format"""
        return f"{self.effect}:{self.resource}:{self.action}"

    def is_more_specific_than(self, other: "ModelPermission") -> bool:
        """Check if this permission is more specific than another"""
        # More hierarchy levels = more specific
        if len(self.resource_hierarchy) > len(other.resource_hierarchy):
            return True

        # More conditions = more specific
        if len(self.conditions) > len(other.conditions):
            return True

        # Temporal constraints = more specific
        if self.temporal_constraints_enabled and not other.temporal_constraints_enabled:
            return True

        # Geographic constraints = more specific
        return bool(
            self.geographic_constraints_enabled
            and not other.geographic_constraints_enabled,
        )

    def _matches_pattern(self, value: str, pattern: str) -> bool:
        """Check if value matches pattern"""
        import fnmatch

        return fnmatch.fnmatch(value, pattern)

    def _ip_in_cidr(self, ip_address: str, cidr: str) -> bool:
        """Check if IP is in CIDR block (simplified)"""
        if "/" not in cidr:
            return ip_address == cidr

        network, prefix_len = cidr.split("/")
        return ip_address.startswith(network.rsplit(".", 1)[0])

    def _evaluate_simple_condition(
        self,
        condition: str,
        context: ModelPermissionEvaluationContext,
    ) -> bool:
        """Simple condition evaluation (placeholder)"""
        # Handle equality checks
        if "==" in condition:
            left, right = condition.split("==", 1)
            left_val = context.get(left.strip())
            right_val = right.strip().strip("'\"")
            return str(left_val) == right_val

        # Handle existence checks
        if condition.strip() in context:
            return bool(context[condition.strip()])

        return True

    @classmethod
    def create_read_permission(
        cls,
        resource: str,
        namespace: str | None = None,
    ) -> "ModelPermission":
        """Create read permission for resource"""
        return cls(
            name=f"read_{resource.replace('/', '_')}",
            resource=resource,
            action="read",
            effect="allow",
            namespace=namespace,
            description=f"Read access to {resource}",
        )

    @classmethod
    def create_write_permission(
        cls,
        resource: str,
        namespace: str | None = None,
    ) -> "ModelPermission":
        """Create write permission for resource"""
        return cls(
            name=f"write_{resource.replace('/', '_')}",
            resource=resource,
            action="write",
            effect="allow",
            namespace=namespace,
            description=f"Write access to {resource}",
            risk_level="medium",
            audit_detail_level="detailed",
        )

    @classmethod
    def create_admin_permission(
        cls,
        resource: str,
        namespace: str | None = None,
    ) -> "ModelPermission":
        """Create admin permission for resource"""
        return cls(
            name=f"admin_{resource.replace('/', '_')}",
            resource=resource,
            action="*",
            effect="allow",
            namespace=namespace,
            description=f"Administrative access to {resource}",
            risk_level="high",
            audit_detail_level="comprehensive",
            approval_required=True,
            require_mfa=True,
        )

    @classmethod
    def create_deny_permission(
        cls,
        resource: str,
        action: str,
        namespace: str | None = None,
    ) -> "ModelPermission":
        """Create deny permission"""
        return cls(
            name=f"deny_{action}_{resource.replace('/', '_')}",
            resource=resource,
            action=action,
            effect="deny",
            namespace=namespace,
            description=f"Deny {action} access to {resource}",
            priority=100,  # High priority for deny rules
            audit_detail_level="comprehensive",
        )

    @classmethod
    def create_emergency_permission(
        cls,
        resource: str,
        action: str,
    ) -> "ModelPermission":
        """Create emergency break-glass permission"""
        return cls(
            name=f"emergency_{action}_{resource.replace('/', '_')}",
            resource=resource,
            action=action,
            effect="allow",
            description=f"Emergency {action} access to {resource}",
            risk_level="critical",
            usage_limits_enabled=True,
            max_uses_total=1,
            audit_detail_level="comprehensive",
            require_mfa=True,
            custom_fields=ModelPermissionCustomFields(
                boolean_fields={"break_glass": True, "emergency_only": True}
            ),
        )

    @classmethod
    def create_time_limited_permission(
        cls,
        resource: str,
        action: str,
        valid_hours: int = 24,
    ) -> "ModelPermission":
        """Create time-limited permission"""
        valid_until = datetime.utcnow().replace(microsecond=0)
        from datetime import timedelta

        valid_until += timedelta(hours=valid_hours)

        return cls(
            name=f"temp_{action}_{resource.replace('/', '_')}",
            resource=resource,
            action=action,
            effect="allow",
            description=f"Temporary {action} access to {resource}",
            temporal_constraints_enabled=True,
            valid_from=datetime.utcnow(),
            valid_until=valid_until,
            audit_detail_level="detailed",
        )
