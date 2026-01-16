"""
Audit metadata model for compliance and audit trails.

This module provides ModelAuditMetadata, a typed model for audit trail
metadata that replaces untyped dict[str, str] fields. It captures audit
identification, categorization, and compliance information.

Thread Safety:
    ModelAuditMetadata is immutable (frozen=True) after creation, making it
    thread-safe for concurrent read access from multiple threads or async tasks.

See Also:
    - omnibase_core.models.context.model_authorization_context: Auth context
    - omnibase_core.models.context.model_checkpoint_metadata: Checkpoint metadata
"""

from pydantic import BaseModel, ConfigDict, Field

__all__ = ["ModelAuditMetadata"]


class ModelAuditMetadata(BaseModel):
    """Audit trail metadata.

    Provides typed audit information for compliance, regulatory requirements,
    and forensic analysis. Supports audit categorization, retention policies,
    and compliance tagging.

    Attributes:
        audit_id: Unique identifier for the audit record. Used to correlate
            audit entries across systems and databases.
        auditor: Identity of the auditor or system component that created
            the audit record (e.g., "system", "user:admin", "service:auth").
        audit_category: Category of the audit event for filtering and reporting
            (e.g., "security", "access", "data_change", "configuration").
        retention_period: Data retention period for compliance purposes
            (e.g., "7d", "30d", "1y", "indefinite").
        compliance_tag: Compliance framework tag for regulatory tracking
            (e.g., "SOC2", "GDPR", "HIPAA", "PCI-DSS").

    Thread Safety:
        This model is frozen and immutable after creation.
        Safe for concurrent read access across threads.

    Example:
        >>> from omnibase_core.models.context import ModelAuditMetadata
        >>>
        >>> audit = ModelAuditMetadata(
        ...     audit_id="audit_abc123",
        ...     auditor="service:onex-gateway",
        ...     audit_category="security",
        ...     retention_period="1y",
        ...     compliance_tag="SOC2",
        ... )
        >>> audit.compliance_tag
        'SOC2'
    """

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    audit_id: str | None = Field(  # string-id-ok: external audit system identifier
        default=None,
        description="Audit record identifier",
    )
    auditor: str | None = Field(
        default=None,
        description="Auditor identity",
    )
    audit_category: str | None = Field(
        default=None,
        description="Audit category",
    )
    retention_period: str | None = Field(
        default=None,
        description="Retention period",
    )
    compliance_tag: str | None = Field(
        default=None,
        description="Compliance tag",
    )
