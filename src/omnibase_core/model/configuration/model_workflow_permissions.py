"""
Workflow permissions model.
"""

from pydantic import BaseModel, Field


class ModelWorkflowPermissions(BaseModel):
    """
    Workflow permissions configuration.
    Replaces Dict[str, Any] for permissions fields.
    """

    # Standard permissions
    actions: str | None = Field(
        None,
        description="Actions permission (read/write/none)",
    )
    attestations: str | None = Field(None, description="Attestations permission")
    checks: str | None = Field(None, description="Checks permission")
    contents: str | None = Field(None, description="Contents permission")
    deployments: str | None = Field(None, description="Deployments permission")
    discussions: str | None = Field(None, description="Discussions permission")
    id_token: str | None = Field(None, description="ID token permission")
    issues: str | None = Field(None, description="Issues permission")
    packages: str | None = Field(None, description="Packages permission")
    pages: str | None = Field(None, description="Pages permission")
    pull_requests: str | None = Field(None, description="Pull requests permission")
    repository_projects: str | None = Field(
        None,
        description="Repository projects permission",
    )
    security_events: str | None = Field(
        None,
        description="Security events permission",
    )
    statuses: str | None = Field(None, description="Statuses permission")

    # Additional permissions
    custom_permissions: dict[str, str] = Field(
        default_factory=dict,
        description="Custom permissions",
    )

    def to_dict(self) -> dict[str, str]:
        """Convert to dictionary for backward compatibility."""
        result = {}
        for field_name, field_value in self.dict(exclude_none=True).items():
            if field_name == "custom_permissions":
                result.update(field_value)
            elif field_name == "id_token":
                result["id-token"] = field_value
            elif field_name == "pull_requests":
                result["pull-requests"] = field_value
            elif field_name == "repository_projects":
                result["repository-projects"] = field_value
            elif field_name == "security_events":
                result["security-events"] = field_value
            else:
                result[field_name] = field_value
        return result
