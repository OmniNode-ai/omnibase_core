"""
Onex Security Context Model.

Pydantic model for Onex security context with SP0 security profile implementation.
Provides authentication, authorization, and audit capabilities.
"""

from datetime import UTC, datetime
from uuid import UUID, uuid4

from pydantic import BaseModel, Field, ValidationInfo, field_validator

from omnibase_core.enums.enum_authentication_method import EnumAuthenticationMethod
from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.enums.enum_data_classification import EnumDataClassification
from omnibase_core.enums.enum_security_profile import EnumSecurityProfile
from omnibase_core.models.core.model_audit_event import ModelAuditEvent
from omnibase_core.models.errors.model_onex_error import ModelOnexError


class ModelOnexSecurityContext(BaseModel):
    """
    Onex Security Context for SP0 Security Profile.

    Provides authentication, authorization, and audit capabilities
    for the bootstrap security profile level.
    """

    # === AUTHENTICATION ===
    user_id: UUID | None = Field(default=None, description="User identifier")
    session_id: UUID | None = Field(default=None, description="Session identifier")
    authentication_token: str | None = Field(
        default=None,
        description="Authentication token",
    )
    authentication_method: EnumAuthenticationMethod = Field(
        default=EnumAuthenticationMethod.NONE,
        description="Authentication method used",
    )
    authentication_timestamp: datetime | None = Field(
        default=None,
        description="Authentication timestamp",
    )
    token_expiry: datetime | None = Field(
        default=None,
        description="Token expiry timestamp",
    )

    # === AUTHORIZATION ===
    authorization_roles: list[str] = Field(
        default_factory=list,
        description="User authorization roles",
    )
    permissions: list[str] = Field(
        default_factory=list,
        description="Specific permissions granted",
    )
    resource_access: dict[str, list[str]] = Field(
        default_factory=dict,
        description="Resource-specific access permissions",
    )

    # === SECURITY PROFILE ===
    security_profile: EnumSecurityProfile = Field(
        default=EnumSecurityProfile.SP0_BOOTSTRAP,
        description="Security profile level",
    )
    data_classification: EnumDataClassification = Field(
        default=EnumDataClassification.INTERNAL,
        description="Data classification level",
    )

    # === CLIENT INFORMATION ===
    client_ip: str | None = Field(default=None, description="Client IP address")
    user_agent: str | None = Field(default=None, description="Client user agent")
    client_fingerprint: str | None = Field(
        default=None,
        description="Client fingerprint",
    )

    # === AUDIT TRAIL ===
    audit_events: list[ModelAuditEvent] = Field(
        default_factory=list,
        description="Security audit events",
    )
    audit_enabled: bool = Field(
        default=True,
        description="Whether audit logging is enabled",
    )

    # === ENCRYPTION ===
    encryption_required: bool = Field(
        default=True,
        description="Whether encryption is required",
    )
    encryption_algorithm: str | None = Field(
        default=None,
        description="Encryption algorithm used",
    )

    # === VALIDATION METADATA ===
    context_id: UUID = Field(
        default_factory=uuid4,
        description="Security context identifier",
    )
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="Context creation time",
    )
    last_validated: datetime | None = Field(
        default=None,
        description="Last validation timestamp",
    )

    # Config imported from model_onex_security_context_config.py

    @field_validator("token_expiry")
    @classmethod
    def validate_token_expiry(
        cls,
        v: datetime | None,
        info: ValidationInfo,
    ) -> datetime | None:
        """Validate token expiry is in the future."""
        if v is not None and v <= datetime.now(UTC):
            msg = "Token expiry must be in the future"
            raise ModelOnexError(
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                message=msg,
            )
        return v

    @field_validator("authentication_timestamp")
    @classmethod
    def validate_auth_timestamp(cls, v: datetime | None) -> datetime | None:
        """Validate authentication timestamp is not in the future."""
        if v is not None and v > datetime.now(UTC):
            msg = "Authentication timestamp cannot be in the future"
            raise ModelOnexError(
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                message=msg,
            )
        return v

    @field_validator("client_ip")
    @classmethod
    def validate_client_ip(cls, v: str | None) -> str | None:
        """Validate client IP format."""
        if v is not None:
            # Basic IP validation - in production, use proper IP validation library
            import re

            ip_pattern = r"^(\d{1,3}\.){3}\d{1,3}$"
            if not re.match(ip_pattern, v):
                msg = "Invalid IP address format"
                raise ModelOnexError(
                    error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                    message=msg,
                )
        return v

    def is_authenticated(self) -> bool:
        """Check if context represents an authenticated user."""
        return (
            self.authentication_method != EnumAuthenticationMethod.NONE
            and self.user_id is not None
            and (self.token_expiry is None or self.token_expiry > datetime.now(UTC))
        )

    def has_role(self, role: str) -> bool:
        """Check if context has specific role."""
        return role in self.authorization_roles

    def has_permission(self, permission: str) -> bool:
        """Check if context has specific permission."""
        return permission in self.permissions

    def has_resource_access(self, resource: str, access_type: str) -> bool:
        """Check if context has specific resource access."""
        return (
            resource in self.resource_access
            and access_type in self.resource_access[resource]
        )

    def is_token_expired(self) -> bool:
        """Check if authentication token is expired."""
        return self.token_expiry is not None and self.token_expiry <= datetime.now(UTC)

    def get_security_level(self) -> int:
        """Get numeric security level for comparison."""
        levels = {
            EnumSecurityProfile.SP0_BOOTSTRAP: 0,
            EnumSecurityProfile.SP1_BASELINE: 1,
            EnumSecurityProfile.SP2_PRODUCTION: 2,
            EnumSecurityProfile.SP3_HIGH_ASSURANCE: 3,
        }
        return levels.get(self.security_profile, 0)

    def meets_security_requirement(self, required_profile: EnumSecurityProfile) -> bool:
        """Check if context meets security requirement."""
        required_levels = {
            EnumSecurityProfile.SP0_BOOTSTRAP: 0,
            EnumSecurityProfile.SP1_BASELINE: 1,
            EnumSecurityProfile.SP2_PRODUCTION: 2,
            EnumSecurityProfile.SP3_HIGH_ASSURANCE: 3,
        }
        return self.get_security_level() >= required_levels.get(required_profile, 0)

    def add_audit_event(
        self,
        event_type: str,
        action: str,
        outcome: str,
        resource: str | None = None,
        additional_data: dict[str, str] | None = None,
    ) -> "ModelOnexSecurityContext":
        """
        Add audit event to the security context.

        Args:
            event_type: Type of audit event
            action: Action being performed
            outcome: Action outcome
            resource: Resource being accessed
            additional_data: Additional audit data

        Returns:
            New security context with added audit event
        """
        if not self.audit_enabled:
            return self

        audit_event = ModelAuditEvent(
            event_type=event_type,
            actor=str(self.user_id) if self.user_id else None,
            resource=resource,
            action=action,
            outcome=outcome,
            additional_data=additional_data or {},
        )

        new_audit_events = [*self.audit_events, audit_event]
        return self.model_copy(update={"audit_events": new_audit_events})

    def add_role(self, role: str) -> "ModelOnexSecurityContext":
        """Add authorization role."""
        if role not in self.authorization_roles:
            new_roles = [*self.authorization_roles, role]
            return self.model_copy(update={"authorization_roles": new_roles})
        return self

    def add_permission(self, permission: str) -> "ModelOnexSecurityContext":
        """Add permission."""
        if permission not in self.permissions:
            new_permissions = [*self.permissions, permission]
            return self.model_copy(update={"permissions": new_permissions})
        return self

    def add_resource_access(
        self,
        resource: str,
        access_types: list[str],
    ) -> "ModelOnexSecurityContext":
        """Add resource access permissions."""
        new_resource_access = {**self.resource_access}
        if resource in new_resource_access:
            # Merge with existing access types
            existing_access = set(new_resource_access[resource])
            new_access = existing_access.union(set(access_types))
            new_resource_access[resource] = list(new_access)
        else:
            new_resource_access[resource] = access_types

        return self.model_copy(update={"resource_access": new_resource_access})

    def validate_context(self) -> bool:
        """Validate security context for completeness."""
        # SP0 Bootstrap validation - minimal requirements
        if self.security_profile == EnumSecurityProfile.SP0_BOOTSTRAP:
            return (
                self.audit_enabled
                and self.encryption_required
                and len(self.audit_events)
                >= 0  # Allow empty audit events for new contexts
            )

        # Higher security profiles would have additional requirements
        return True

    def sanitize_for_logging(self) -> dict[str, str | None]:
        """Create sanitized version for logging (removes sensitive data)."""
        return {
            "user_id": str(self.user_id) if self.user_id else "anonymous",
            "session_id": str(self.session_id)[:8] + "..." if self.session_id else None,
            "authentication_method": self.authentication_method,
            "security_profile": self.security_profile,
            "data_classification": self.data_classification,
            "client_ip": self.client_ip,
            "audit_enabled": str(self.audit_enabled),
            "encryption_required": str(self.encryption_required),
            "roles_count": str(len(self.authorization_roles)),
            "permissions_count": str(len(self.permissions)),
            "audit_events_count": str(len(self.audit_events)),
        }
