"""
Metadata models for ONEX tool operations.

This module contains Pydantic models used by metadata tools for
file operations, stamping, and metadata management.
"""

from .model_file_info import ModelFileInfo
from .model_file_statistics import ModelFileStatistics
from .model_file_type import (JSON_FILE_TYPE, MARKDOWN_FILE_TYPE,
                              PYTHON_FILE_TYPE, YAML_FILE_TYPE, ModelFileType)
from .model_function_discovery import (ModelClassInfo, ModelFunctionDiscovery,
                                       ModelFunctionSignature, ModelImportInfo)
from .model_hash_algorithm import EnumHashAlgorithm, ModelHashAlgorithm
from .model_hash_result import ModelHashResult
from .model_metadata_block import ModelMetadataBlock
from .model_metadata_dict import ModelMetadataDict
from .model_metadata_properties import ModelMetadataProperties
from .model_scan_summary import ModelScanSummary
from .model_stamping_result import (EnumStampingOperation, EnumStampingStatus,
                                    ModelStampingResult)

__all__ = [
    # File type models
    "ModelFileType",
    "PYTHON_FILE_TYPE",
    "YAML_FILE_TYPE",
    "MARKDOWN_FILE_TYPE",
    "JSON_FILE_TYPE",
    # Hash models
    "EnumHashAlgorithm",
    "ModelHashAlgorithm",
    "ModelHashResult",
    # Metadata models
    "ModelMetadataBlock",
    "ModelFileInfo",
    # Stamping models
    "ModelStampingResult",
    "EnumStampingOperation",
    "EnumStampingStatus",
    # Additional models
    "ModelScanSummary",
    "ModelFileStatistics",
    "ModelMetadataDict",
    "ModelMetadataProperties",
    "ModelFunctionDiscovery",
    "ModelFunctionSignature",
    "ModelClassInfo",
    "ModelImportInfo",
]
