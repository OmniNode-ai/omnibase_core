"""
Version Implementation Model - Tier 3 Metadata.

Pydantic model for implementation file information.
"""

from pydantic import BaseModel, Field

from omnibase_core.models.core.model_version_file import ModelVersionFile


class ModelVersionImplementation(BaseModel):
    """Implementation file information."""

    implementation_file: str = Field(
        default="node.py",
        description="Main implementation file name",
    )
    main_class_name: str = Field(description="Main implementation class name")
    entry_point: str | None = Field(
        default=None,
        description="Entry point for standalone execution",
    )
    namespace: str = Field(description="Python namespace for the implementation")

    # File references
    model_files: list[ModelVersionFile] = Field(
        default_factory=list,
        description="Pydantic model files",
    )
    protocol_files: list[ModelVersionFile] = Field(
        default_factory=list,
        description="Protocol interface files",
    )
    enum_files: list[ModelVersionFile] = Field(
        default_factory=list,
        description="Enumeration definition files",
    )
    contract_files: list[ModelVersionFile] = Field(
        default_factory=list,
        description="Subcontract files",
    )
