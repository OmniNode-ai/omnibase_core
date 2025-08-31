"""
Permission Constraint Metadata Model

Type-safe metadata for permission constraints.
"""

from pydantic import BaseModel, Field

from omnibase_core.model.core.model_custom_fields import ModelCustomFields


class ModelPermissionConstraintMetadata(BaseModel):
    """
    Type-safe metadata for permission constraints.

    Provides additional context and documentation for constraints.
    """

    # Documentation
    description: str | None = Field(
        None,
        description="Human-readable description of these constraints",
    )

    business_justification: str | None = Field(
        None,
        description="Business justification for these constraints",
    )

    # Ownership and management
    owner: str | None = Field(None, description="Owner of these constraints")

    owner_team: str | None = Field(
        None,
        description="Team responsible for these constraints",
    )

    contact_email: str | None = Field(
        None,
        description="Contact email for questions",
    )

    # Lifecycle
    created_date: str | None = Field(
        None,
        description="When constraints were created (ISO format)",
    )

    created_by: str | None = Field(None, description="Who created these constraints")

    last_modified_date: str | None = Field(
        None,
        description="When constraints were last modified (ISO format)",
    )

    last_modified_by: str | None = Field(
        None,
        description="Who last modified these constraints",
    )

    review_date: str | None = Field(
        None,
        description="Next scheduled review date (ISO format)",
    )

    expiry_date: str | None = Field(
        None,
        description="When these constraints expire (ISO format)",
    )

    # References
    policy_references: list[str] = Field(
        default_factory=list,
        description="Related policy document references",
    )

    compliance_references: list[str] = Field(
        default_factory=list,
        description="Compliance requirement references",
    )

    ticket_references: list[str] = Field(
        default_factory=list,
        description="Related ticket/issue references",
    )

    # Tags and categorization
    tags: list[str] = Field(default_factory=list, description="Tags for categorization")

    constraint_category: str | None = Field(
        None,
        description="Category of constraints",
        pattern="^(security|compliance|operational|business|temporary)$",
    )

    environment: str | None = Field(
        None,
        description="Environment these constraints apply to",
        pattern="^(all|production|staging|development|test)$",
    )

    # Impact analysis
    estimated_users_affected: int | None = Field(
        None,
        description="Estimated number of users affected",
        ge=0,
    )

    business_impact: str | None = Field(
        None,
        description="Business impact assessment",
        pattern="^(minimal|low|moderate|high|critical)$",
    )

    # Custom metadata
    custom_fields: ModelCustomFields | None = Field(
        None,
        description="Additional custom metadata",
    )
