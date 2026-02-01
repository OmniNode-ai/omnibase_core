"""ONEX-compatible Permission Model.

Comprehensive permission model for fine-grained access control with support for
resource hierarchies, conditional access, approval workflows, and audit trails.
Fully ONEX-compatible with proper error handling, validation, and business logic.
"""

import fnmatch
from datetime import UTC, datetime, timedelta
from typing import Self
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field, field_validator

from omnibase_core.constants import MAX_DESCRIPTION_LENGTH, MAX_IDENTIFIER_LENGTH
from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.models.errors.model_onex_error import ModelOnexError
from omnibase_core.models.primitives.model_semver import ModelSemVer
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
    ONEX-compatible extensible permission model for fine-grained access control.

    Supports resource hierarchies, conditional access, enterprise features like
    delegation, approval workflows, and comprehensive audit trails.
    """

    model_config = ConfigDict(
        validate_assignment=True,
        extra="forbid",
    )

    # Core identifiers
    permission_id: UUID = Field(
        default_factory=uuid4,
        description="Unique permission identifier",
    )

    name: str = Field(
        default=...,
        description="Human-readable permission name",
        min_length=1,
        max_length=MAX_IDENTIFIER_LENGTH,
        pattern="^[a-zA-Z][a-zA-Z0-9_\\-\\s]*$",
    )

    resource: str = Field(
        default=...,
        description="Resource identifier or pattern",
        min_length=1,
        max_length=500,
        pattern="^[a-z][a-z0-9:._\\-/*]*$",
    )

    action: str = Field(
        default=...,
        description="Action on resource (or '*' for all actions)",
        min_length=1,
        max_length=50,
        pattern="^([a-z][a-z0-9_]*|\\*)$",
    )

    effect: str = Field(
        default="allow",
        description="Permission effect",
        pattern="^(allow|deny)$",
    )

    # Scope and hierarchy
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

    # Conditional access
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

    # Namespace and versioning
    namespace: str | None = Field(
        default=None,
        description="Permission namespace for third-party isolation",
        pattern="^[a-z][a-z0-9_-]*$",
        max_length=50,
    )

    version: ModelSemVer = Field(
        ...,  # REQUIRED - specify in contract
        description="Permission definition version",
    )

    # Usage limits
    usage_limits_enabled: bool = Field(
        default=False,
        description="Whether usage limits are enforced",
    )

    max_uses_total: int | None = Field(
        default=None,
        description="Maximum total uses",
        ge=0,
    )

    max_uses_per_day: int | None = Field(
        default=None,
        description="Maximum uses per day",
        ge=0,
    )

    max_uses_per_hour: int | None = Field(
        default=None,
        description="Maximum uses per hour",
        ge=0,
    )

    # Approval workflow
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
        le=10,
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
        default=None,
        description="Permission valid from timestamp",
    )

    valid_until: datetime | None = Field(
        default=None,
        description="Permission valid until timestamp",
    )

    time_of_day_start: str | None = Field(
        default=None,
        description="Daily start time (HH:MM)",
        pattern="^([01]?[0-9]|2[0-3]):[0-5][0-9]$",
    )

    time_of_day_end: str | None = Field(
        default=None,
        description="Daily end time (HH:MM)",
        pattern="^([01]?[0-9]|2[0-3]):[0-5][0-9]$",
    )

    days_of_week: list[int] = Field(
        default_factory=lambda: list(range(7)),
        description="Valid days of week (0=Monday)",
        max_length=7,
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

    require_mfa: bool = Field(
        default=False,
        description="Whether MFA is required",
    )

    require_secure_connection: bool = Field(
        default=False,
        description="Whether secure connection is required",
    )

    # Metadata and extensions
    description: str | None = Field(
        default=None,
        description="Human-readable description",
        max_length=MAX_DESCRIPTION_LENGTH,
    )

    tags: list[str] = Field(
        default_factory=list,
        description="Permission tags for organization",
    )

    compliance_tags: list[str] = Field(
        default_factory=list,
        description="Compliance framework tags",
    )

    custom_fields: ModelPermissionCustomFields = Field(
        default_factory=lambda: ModelPermissionCustomFields(),
        description="Custom extension fields",
    )

    # Timestamps
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="Creation timestamp",
    )

    created_by: str | None = Field(
        default=None,
        description="Creator identifier",
        max_length=MAX_IDENTIFIER_LENGTH,
    )

    updated_at: datetime | None = Field(
        default=None,
        description="Last update timestamp",
    )

    updated_by: str | None = Field(
        default=None,
        description="Last updater identifier",
        max_length=MAX_IDENTIFIER_LENGTH,
    )

    metadata: ModelPermissionMetadata = Field(
        default_factory=lambda: ModelPermissionMetadata(
            tags=[],
            category=None,
            priority=None,
            source_system=None,
            external_id=None,
            notes=None,
        ),
        description="Additional metadata",
    )

    # === Field Validators ===

    @field_validator("resource_hierarchy")
    @classmethod
    def validate_resource_hierarchy(cls, v: list[str]) -> list[str]:
        if len(v) > 10:
            raise ModelOnexError(
                message="Resource hierarchy cannot exceed 10 levels",
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
            )
        return v

    @field_validator("resource_patterns")
    @classmethod
    def validate_resource_patterns(cls, v: list[str]) -> list[str]:
        if len(v) > 20:
            raise ModelOnexError(
                message="Maximum 20 resource patterns allowed",
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
            )
        return v

    @field_validator("conditions")
    @classmethod
    def validate_conditions(cls, v: list[str]) -> list[str]:
        if len(v) > 50:
            raise ModelOnexError(
                message="Maximum 50 conditions allowed",
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
            )
        return v

    @field_validator("tags")
    @classmethod
    def validate_tags(cls, v: list[str]) -> list[str]:
        if len(v) > 20:
            raise ModelOnexError(
                message="Maximum 20 tags allowed",
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
            )
        for tag in v:
            if len(tag) > 50:
                raise ModelOnexError(
                    message=f"Tag '{tag}' exceeds maximum length of 50",
                    error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                )
        return v

    @field_validator("approval_types")
    @classmethod
    def validate_approval_types(cls, v: list[str]) -> list[str]:
        if len(v) > 10:
            raise ModelOnexError(
                message="Maximum 10 approval types allowed",
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
            )
        return v

    @field_validator("allowed_countries")
    @classmethod
    def validate_allowed_countries(cls, v: list[str]) -> list[str]:
        if len(v) > 50:
            raise ModelOnexError(
                message="Maximum 50 countries allowed",
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
            )
        return v

    @field_validator("allowed_ip_ranges")
    @classmethod
    def validate_allowed_ip_ranges(cls, v: list[str]) -> list[str]:
        if len(v) > 20:
            raise ModelOnexError(
                message="Maximum 20 IP ranges allowed",
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
            )
        return v

    # === Resource Matching Methods ===

    def matches_resource(self, resource_path: str) -> bool:
        import fnmatch

        # Direct match
        if self.resource == resource_path:
            return True

        # Pattern matching
        if self.resource_patterns:
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
            return fnmatch.fnmatch(resource_path, self.resource)

        return False

    # === Temporal Validation Methods ===

    def is_temporally_valid(self, current_time: datetime | None = None) -> bool:
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

        # Check day of week
        current_day = current_time.weekday()
        return current_day in self.days_of_week

    def is_expired(self) -> bool:
        if not self.valid_until:
            return False
        return datetime.now(UTC) > self.valid_until

    def is_active(self) -> bool:
        if not self.valid_from:
            return True
        return datetime.now(UTC) >= self.valid_from

    # === Geographic Validation Methods ===

    def is_geographically_valid(
        self,
        country_code: str | None = None,
        ip_address: str | None = None,
    ) -> bool:
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

    # === Condition Evaluation Methods ===

    def evaluate_conditions(self, context: ModelPermissionEvaluationContext) -> bool:
        if not self.conditions:
            return True

        for condition in self.conditions:
            try:
                if not self._evaluate_simple_condition(condition, context):
                    return False
            except (AttributeError, KeyError, OSError, TypeError, ValueError):
                # fallback-ok: Security fail-safe - deny access on malformed conditions
                return False  # Fail safe

        return True

    # === Usage Management Methods ===

    def is_usage_allowed(self, current_usage: dict[str, int]) -> bool:
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

    def get_usage_summary(self, current_usage: dict[str, int]) -> dict[str, str]:
        """Get usage summary with remaining quotas."""
        summary = {
            "status": "allowed" if self.is_usage_allowed(current_usage) else "blocked",
            "limits_enabled": str(self.usage_limits_enabled),
        }

        if self.usage_limits_enabled:
            if self.max_uses_total:
                remaining = self.max_uses_total - current_usage.get("total", 0)
                summary["total_remaining"] = str(max(0, remaining))

            if self.max_uses_per_day:
                remaining = self.max_uses_per_day - current_usage.get("today", 0)
                summary["daily_remaining"] = str(max(0, remaining))

            if self.max_uses_per_hour:
                remaining = self.max_uses_per_hour - current_usage.get("this_hour", 0)
                summary["hourly_remaining"] = str(max(0, remaining))

        return summary

    # === Utility Methods ===

    def get_qualified_name(self) -> str:
        """Get qualified permission name with namespace."""
        if self.namespace:
            return f"{self.namespace}:{self.name}"
        return self.name

    def to_statement(self) -> str:
        """Convert to permission statement format."""
        return f"{self.effect}:{self.resource}:{self.action}"

    def is_more_specific_than(self, other: "ModelPermission") -> bool:
        """Check if this permission is more specific than another."""
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

    def get_risk_score(self) -> int:
        """Calculate risk score based on permission attributes."""
        score = 0

        # Base risk level
        risk_levels = {"low": 10, "medium": 25, "high": 50, "critical": 100}
        score += risk_levels.get(self.risk_level, 25)

        # Effect (deny is lower risk)
        if self.effect == "deny":
            score -= 10

        # Scope modifiers
        if self.scope_type == "global":
            score += 20
        elif self.scope_type == "organizational":
            score += 10

        # Constraints reduce risk
        if self.temporal_constraints_enabled:
            score -= 5
        if self.geographic_constraints_enabled:
            score -= 5
        if self.usage_limits_enabled:
            score -= 5

        # Security requirements
        if self.require_mfa:
            score -= 10
        if self.approval_required:
            score -= 15

        return max(0, min(100, score))

    def update_timestamp(self) -> None:
        """Update the last modified timestamp."""
        self.updated_at = datetime.now(UTC)

    # === Private Helper Methods ===

    def _matches_pattern(self, value: str, pattern: str) -> bool:
        """Check if value matches pattern."""

        return fnmatch.fnmatch(value, pattern)

    def _ip_in_cidr(self, ip_address: str, cidr: str) -> bool:
        """Check if IP is in CIDR block (simplified)."""
        if "/" not in cidr:
            # Treat as prefix match (e.g., "10.0.0" matches "10.0.0.x")
            return ip_address.startswith(cidr + ".")

        network, _ = cidr.split("/")
        return ip_address.startswith(network.rsplit(".", 1)[0])

    def _evaluate_simple_condition(
        self,
        condition: str,
        context: ModelPermissionEvaluationContext,
    ) -> bool:
        """Simple condition evaluation (placeholder)."""
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

    # === Factory Methods ===

    @classmethod
    def create_read_permission(
        cls,
        resource: str,
        namespace: str | None = None,
        description: str | None = None,
    ) -> Self:
        """Create read permission for resource."""
        return cls(
            name=f"read_{resource.replace('/', '_')}",
            resource=resource,
            action="read",
            effect="allow",
            namespace=namespace,
            description=description or f"Read access to {resource}",
            risk_level="low",
            version=ModelSemVer(major=1, minor=0, patch=0),
            max_uses_total=None,
            max_uses_per_day=None,
            max_uses_per_hour=None,
            valid_from=None,
            valid_until=None,
            time_of_day_start=None,
            time_of_day_end=None,
            created_by=None,
            updated_at=None,
            updated_by=None,
        )

    @classmethod
    def create_write_permission(
        cls,
        resource: str,
        namespace: str | None = None,
        description: str | None = None,
    ) -> Self:
        """Create write permission for resource."""
        return cls(
            name=f"write_{resource.replace('/', '_')}",
            resource=resource,
            action="write",
            effect="allow",
            namespace=namespace,
            description=description or f"Write access to {resource}",
            risk_level="medium",
            audit_detail_level="detailed",
            version=ModelSemVer(major=1, minor=0, patch=0),
            max_uses_total=None,
            max_uses_per_day=None,
            max_uses_per_hour=None,
            valid_from=None,
            valid_until=None,
            time_of_day_start=None,
            time_of_day_end=None,
            created_by=None,
            updated_at=None,
            updated_by=None,
        )

    @classmethod
    def create_admin_permission(
        cls,
        resource: str,
        namespace: str | None = None,
        description: str | None = None,
    ) -> Self:
        """Create admin permission for resource."""
        return cls(
            name=f"admin_{resource.replace('/', '_')}",
            resource=resource,
            action="*",
            effect="allow",
            namespace=namespace,
            description=description or f"Administrative access to {resource}",
            risk_level="high",
            audit_detail_level="comprehensive",
            approval_required=True,
            require_mfa=True,
            version=ModelSemVer(major=1, minor=0, patch=0),
            max_uses_total=None,
            max_uses_per_day=None,
            max_uses_per_hour=None,
            valid_from=None,
            valid_until=None,
            time_of_day_start=None,
            time_of_day_end=None,
            created_by=None,
            updated_at=None,
            updated_by=None,
        )

    @classmethod
    def create_deny_permission(
        cls,
        resource: str,
        action: str,
        namespace: str | None = None,
        description: str | None = None,
    ) -> Self:
        """Create deny permission."""
        return cls(
            name=f"deny_{action}_{resource.replace('/', '_')}",
            resource=resource,
            action=action,
            effect="deny",
            namespace=namespace,
            description=description or f"Deny {action} access to {resource}",
            priority=100,  # High priority for deny rules
            audit_detail_level="comprehensive",
            version=ModelSemVer(major=1, minor=0, patch=0),
            max_uses_total=None,
            max_uses_per_day=None,
            max_uses_per_hour=None,
            valid_from=None,
            valid_until=None,
            time_of_day_start=None,
            time_of_day_end=None,
            created_by=None,
            updated_at=None,
            updated_by=None,
        )

    @classmethod
    def create_emergency_permission(
        cls,
        resource: str,
        action: str,
        description: str | None = None,
    ) -> Self:
        """Create emergency break-glass permission."""
        return cls(
            name=f"emergency_{action}_{resource.replace('/', '_')}",
            resource=resource,
            action=action,
            effect="allow",
            description=description or f"Emergency {action} access to {resource}",
            risk_level="critical",
            usage_limits_enabled=True,
            max_uses_total=1,
            audit_detail_level="comprehensive",
            require_mfa=True,
            version=ModelSemVer(major=1, minor=0, patch=0),
            custom_fields=ModelPermissionCustomFields(
                boolean_fields={"break_glass": True, "emergency_only": True}
            ),
            max_uses_per_day=None,
            max_uses_per_hour=None,
            valid_from=None,
            valid_until=None,
            time_of_day_start=None,
            time_of_day_end=None,
            namespace=None,
            created_by=None,
            updated_at=None,
            updated_by=None,
        )

    @classmethod
    def create_time_limited_permission(
        cls,
        resource: str,
        action: str,
        valid_hours: int = 24,
        namespace: str | None = None,
        description: str | None = None,
    ) -> Self:
        """Create time-limited permission."""
        valid_until = datetime.now(UTC).replace(microsecond=0) + timedelta(
            hours=valid_hours
        )

        return cls(
            name=f"temp_{action}_{resource.replace('/', '_')}",
            resource=resource,
            action=action,
            effect="allow",
            namespace=namespace,
            description=description or f"Temporary {action} access to {resource}",
            temporal_constraints_enabled=True,
            valid_from=datetime.now(UTC),
            valid_until=valid_until,
            audit_detail_level="detailed",
            version=ModelSemVer(major=1, minor=0, patch=0),
            max_uses_total=None,
            max_uses_per_day=None,
            max_uses_per_hour=None,
            time_of_day_start=None,
            time_of_day_end=None,
            created_by=None,
            updated_at=None,
            updated_by=None,
        )
