"""
File Operation Rollback Data Model for Intelligence File Operations.

Represents operation-specific rollback information for atomic file operations.
"""

from typing import Optional

from pydantic import BaseModel, Field


class model_file_operation_rollback_data(BaseModel):
    """
    Model representing operation-specific rollback data for file operations.

    Contains the specific data needed to perform or rollback individual
    file operations like write, delete, etc.
    """

    content: Optional[str] = Field(
        None, description="Content to write or that was written"
    )

    encoding: str = Field(default="utf-8", description="File encoding to use")

    create_backup: bool = Field(
        default=True, description="Whether to create backup before operation"
    )

    file_existed: bool = Field(
        default=False, description="Whether file existed before operation"
    )
