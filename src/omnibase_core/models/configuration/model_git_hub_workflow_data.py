"""GitHub Actions workflow data model."""

from pydantic import BaseModel, ConfigDict

__all__ = ["ModelGitHubWorkflowData"]


class ModelGitHubWorkflowData(BaseModel):
    """Serializable workflow data structure.

    This model represents the serialized form of a GitHub Actions workflow.
    It uses broader types to accommodate all valid GitHub workflow YAML formats.

    Field Types:
        on: Supports string ("push"), list (["push", "pull_request"]), or dict
            with nested event configuration ({"push": {"branches": ["main"]}}).
        concurrency: Supports string (group name) or dict with group and
            cancel-in-progress options.
        permissions: Supports string ("read-all", "write-all") or dict mapping
            permission keys to values ("read", "write", "none").
        defaults: Nested dict structure containing "run" with "shell" and
            "working-directory" options.
    """

    # from_attributes=True allows Pydantic to accept objects with matching
    # attributes even when class identity differs (e.g., in pytest-xdist
    # parallel execution where model classes are imported in separate workers).
    # See CLAUDE.md section "Pydantic from_attributes=True for Value Objects".
    model_config = ConfigDict(
        frozen=False,
        strict=False,
        extra="forbid",
        from_attributes=True,
    )

    name: str
    # GitHub 'on' field: string, list of strings, or dict with event config
    # Examples: "push", ["push", "pull_request"], {"push": {"branches": ["main"]}}
    on: str | list[str] | dict[str, object] | None = None
    jobs: dict[str, dict[str, object]]
    env: dict[str, str] | None = None
    # GitHub 'defaults' field: nested dict with 'run' containing shell/working-directory
    # Example: {"run": {"shell": "bash", "working-directory": "scripts"}}
    defaults: dict[str, dict[str, str]] | None = None
    # GitHub 'concurrency' field: string (group name) or dict with options
    # Examples: "my-group", {"group": "my-group", "cancel-in-progress": true}
    concurrency: str | dict[str, str | bool] | None = None
    # GitHub 'permissions' field: string shorthand or dict of permission mappings
    # Examples: "read-all", {"contents": "read", "pull-requests": "write"}
    permissions: str | dict[str, str] | None = None
