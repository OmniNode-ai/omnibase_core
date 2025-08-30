"""
Permission Constraint Metadata Model

Type-safe metadata for permission constraints.
"""

from typing import List, Optional

from pydantic import BaseModel, Field

from ..core.model_custom_fields import ModelCustomFields


class ModelPermissionConstraintMetadata(BaseModel):
    """
    Type-safe metadata for permission constraints.

    Provides additional context and documentation for constraints.
    """

    # Documentation
    description: Optional[str] = Field(
        None, description="Human-readable description of these constraints"
    )

    business_justification: Optional[str] = Field(
        None, description="Business justification for these constraints"
    )

    # Ownership and management
    owner: Optional[str] = Field(None, description="Owner of these constraints")

    owner_team: Optional[str] = Field(
        None, description="Team responsible for these constraints"
    )

    contact_email: Optional[str] = Field(
        None, description="Contact email for questions"
    )

    # Lifecycle
    created_date: Optional[str] = Field(
        None, description="When constraints were created (ISO format)"
    )

    created_by: Optional[str] = Field(None, description="Who created these constraints")

    last_modified_date: Optional[str] = Field(
        None, description="When constraints were last modified (ISO format)"
    )

    last_modified_by: Optional[str] = Field(
        None, description="Who last modified these constraints"
    )

    review_date: Optional[str] = Field(
        None, description="Next scheduled review date (ISO format)"
    )

    expiry_date: Optional[str] = Field(
        None, description="When these constraints expire (ISO format)"
    )

    # References
    policy_references: List[str] = Field(
        default_factory=list, description="Related policy document references"
    )

    compliance_references: List[str] = Field(
        default_factory=list, description="Compliance requirement references"
    )

    ticket_references: List[str] = Field(
        default_factory=list, description="Related ticket/issue references"
    )

    # Tags and categorization
    tags: List[str] = Field(default_factory=list, description="Tags for categorization")

    constraint_category: Optional[str] = Field(
        None,
        description="Category of constraints",
        pattern="^(security|compliance|operational|business|temporary)$",
    )

    environment: Optional[str] = Field(
        None,
        description="Environment these constraints apply to",
        pattern="^(all|production|staging|development|test)$",
    )

    # Impact analysis
    estimated_users_affected: Optional[int] = Field(
        None, description="Estimated number of users affected", ge=0
    )

    business_impact: Optional[str] = Field(
        None,
        description="Business impact assessment",
        pattern="^(minimal|low|moderate|high|critical)$",
    )

    # Custom metadata
    custom_fields: Optional[ModelCustomFields] = Field(
        None, description="Additional custom metadata"
    )
