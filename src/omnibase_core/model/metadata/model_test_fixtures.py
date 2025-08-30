"""
Pydantic models for test fixtures and test data structures.
"""

from typing import List

from pydantic import BaseModel, Field

from .model_file_type import ModelFileType
from .model_hash_algorithm import EnumHashAlgorithm
from .model_metadata_block import ModelMetadataBlock
from .model_stamping_result import EnumStampingOperation, EnumStampingStatus


class ModelHashTestVector(BaseModel):
    """Model for hash computation test vectors."""

    content: str = Field(..., description="Content to hash")
    algorithm: EnumHashAlgorithm = Field(..., description="Hash algorithm to use")
    expected_hash: str = Field(..., description="Expected hash result")
    input_size: int = Field(..., description="Size of input content in bytes")


class ModelFileTypeTestCase(BaseModel):
    """Model for file type detection test cases."""

    file_path: str = Field(..., description="Test file path")
    content: str = Field(..., description="File content for testing")
    expected_type: str = Field(..., description="Expected file type name")
    detection_method: str = Field(
        ..., description="Detection method (extension, content, heuristic)"
    )


class ModelStampingTestScenario(BaseModel):
    """Model for file stamping test scenarios."""

    name: str = Field(..., description="Scenario name")
    operation: EnumStampingOperation = Field(
        ..., description="Stamping operation to perform"
    )
    file_content: str = Field(..., description="Initial file content")
    file_type: ModelFileType = Field(..., description="File type information")
    metadata: ModelMetadataBlock = Field(..., description="Metadata to stamp")
    expected_status: EnumStampingStatus = Field(
        ..., description="Expected operation status"
    )
    should_create_backup: bool = Field(
        False, description="Whether backup should be created"
    )


class ModelDirectoryFile(BaseModel):
    """Model for representing a file in a directory structure."""

    name: str = Field(..., description="File name")
    content: str = Field(..., description="File content")
    is_directory: bool = Field(False, description="Whether this is a directory")


class ModelDirectoryStructure(BaseModel):
    """Model for representing directory structures in tests."""

    name: str = Field(..., description="Directory name")
    files: List[ModelDirectoryFile] = Field(
        default_factory=list, description="Files in directory"
    )
    subdirectories: List["ModelDirectoryStructure"] = Field(
        default_factory=list, description="Subdirectories"
    )


class ModelTestFilePatterns(BaseModel):
    """Model for test file patterns."""

    python_files: List[str] = Field(
        default_factory=list, description="Python file patterns"
    )
    config_files: List[str] = Field(
        default_factory=list, description="Configuration file patterns"
    )
    doc_files: List[str] = Field(
        default_factory=list, description="Documentation file patterns"
    )
    all_files: List[str] = Field(default_factory=list, description="All file patterns")
    source_files: List[str] = Field(
        default_factory=list, description="Source code file patterns"
    )


# Enable forward references
ModelDirectoryStructure.model_rebuild()
