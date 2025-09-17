"""
Post-Push Hook Status Model for Intelligence System.

Represents the status of post-push hook installation.
"""

from pydantic import BaseModel, Field


class model_post_push_hook_status(BaseModel):
    """
    Model representing post-push hook installation status.

    Contains all relevant information about the current state of the
    post-push hook installation.
    """

    installed: bool = Field(..., description="Whether ONEX post-push hook is installed")

    hook_file: str = Field(..., description="Path to the hook file")

    hook_exists: bool = Field(..., description="Whether hook file exists on filesystem")

    hook_executable: bool = Field(
        ...,
        description="Whether hook file has execute permissions",
    )

    backup_exists: bool = Field(
        ...,
        description="Whether backup of original hook exists",
    )

    auto_install_enabled: bool = Field(
        ...,
        description="Whether automatic pre-commit hook installation is enabled",
    )
