"""
Workflow permissions model.
"""

from typing import Dict, Optional

from pydantic import BaseModel, Field


class ModelWorkflowPermissions(BaseModel):
    """
    Workflow permissions configuration.
    Replaces Dict[str, Any] for permissions fields.
    """

    # Standard permissions
    actions: Optional[str] = Field(
        None, description="Actions permission (read/write/none)"
    )
    attestations: Optional[str] = Field(None, description="Attestations permission")
    checks: Optional[str] = Field(None, description="Checks permission")
    contents: Optional[str] = Field(None, description="Contents permission")
    deployments: Optional[str] = Field(None, description="Deployments permission")
    discussions: Optional[str] = Field(None, description="Discussions permission")
    id_token: Optional[str] = Field(None, description="ID token permission")
    issues: Optional[str] = Field(None, description="Issues permission")
    packages: Optional[str] = Field(None, description="Packages permission")
    pages: Optional[str] = Field(None, description="Pages permission")
    pull_requests: Optional[str] = Field(None, description="Pull requests permission")
    repository_projects: Optional[str] = Field(
        None, description="Repository projects permission"
    )
    security_events: Optional[str] = Field(
        None, description="Security events permission"
    )
    statuses: Optional[str] = Field(None, description="Statuses permission")

    # Additional permissions
    custom_permissions: Dict[str, str] = Field(
        default_factory=dict, description="Custom permissions"
    )

    def to_dict(self) -> Dict[str, str]:
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
