"""
Workflow permissions model.
"""

from pydantic import BaseModel, Field


class ModelWorkflowPermissions(BaseModel):
    """
    Workflow permissions configuration.
    Replaces Dict[str, Any] for permissions fields.
    """

    actions: str = Field(
        default="read", description="Actions permission (read/write/none)"
    )
    attestations: str = Field(default="read", description="Attestations permission")
    checks: str = Field(default="read", description="Checks permission")
    contents: str = Field(default="read", description="Contents permission")
    deployments: str = Field(default="read", description="Deployments permission")
    discussions: str = Field(default="read", description="Discussions permission")
    id_token: str = Field(default="write", description="ID token permission")
    issues: str = Field(default="read", description="Issues permission")
    packages: str = Field(default="read", description="Packages permission")
    pages: str = Field(default="read", description="Pages permission")
    pull_requests: str = Field(default="read", description="Pull requests permission")
    repository_projects: str = Field(
        default="read", description="Repository projects permission"
    )
    security_events: str = Field(
        default="read", description="Security events permission"
    )
    statuses: str = Field(default="read", description="Statuses permission")
    custom_permissions: dict[str, str] = Field(
        default_factory=dict, description="Custom permissions"
    )

    @property
    def permission_summary(self) -> dict[str, str]:
        """Get comprehensive permissions summary."""
        standard_permissions = {
            "actions": self.actions,
            "attestations": self.attestations,
            "checks": self.checks,
            "contents": self.contents,
            "deployments": self.deployments,
            "discussions": self.discussions,
            "id-token": self.id_token,
            "issues": self.issues,
            "packages": self.packages,
            "pages": self.pages,
            "pull-requests": self.pull_requests,
            "repository-projects": self.repository_projects,
            "security-events": self.security_events,
            "statuses": self.statuses,
        }
        result = {**standard_permissions, **self.custom_permissions}
        return result

    @property
    def write_permissions(self) -> list[str]:
        """Get list of permissions set to 'write'."""
        write_perms = []
        summary = self.permission_summary
        for perm_name, perm_value in summary.items():
            if perm_value == "write":
                write_perms.append(perm_name)
        return write_perms

    @property
    def read_only_permissions(self) -> list[str]:
        """Get list of permissions set to 'read'."""
        read_perms = []
        summary = self.permission_summary
        for perm_name, perm_value in summary.items():
            if perm_value == "read":
                read_perms.append(perm_name)
        return read_perms

    @property
    def denied_permissions(self) -> list[str]:
        """Get list of permissions set to 'none'."""
        denied_perms = []
        summary = self.permission_summary
        for perm_name, perm_value in summary.items():
            if perm_value == "none":
                denied_perms.append(perm_name)
        return denied_perms
