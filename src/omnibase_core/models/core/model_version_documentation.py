"""
Version Documentation Model - Tier 3 Metadata.

Pydantic model for version documentation information.
"""

from pydantic import BaseModel, Field

from omnibase_core.models.core.model_version_file import ModelVersionFile


class ModelVersionDocumentation(BaseModel):
    """Version documentation information."""

    documentation_files: list[ModelVersionFile] = Field(
        default_factory=list,
        description="Documentation files",
    )
    readme_file: str | None = Field(
        default="README.md",
        description="README file name",
    )
    api_documentation: str | None = Field(
        default=None,
        description="API documentation file or URL",
    )
    changelog_entry: str | None = Field(
        default=None,
        description="Changelog entry for this version",
    )
    migration_guide: str | None = Field(
        default=None,
        description="Migration guide from previous versions",
    )
