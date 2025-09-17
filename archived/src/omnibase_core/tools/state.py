"""State models for model splitter tool."""

from enum import Enum

from pydantic import BaseModel, Field

from omnibase_core.core.base_models import OnexInputState, OnexOutputState


class EnumSplitMode(str, Enum):
    """Mode for splitting models."""

    ONE_PER_FILE = "one_per_file"
    BY_DEPENDENCY = "by_dependency"
    BY_TYPE = "by_type"
    PRESERVE_STRUCTURE = "preserve_structure"


class ModelSplitterConfig(BaseModel):
    """Configuration for model splitting operations."""

    dry_run: bool = Field(
        default=False,
        description="If true, only show what would be done without making changes",
    )
    create_backups: bool = Field(
        default=True,
        description="Whether to create backups before modifying files",
    )
    update_imports: bool = Field(
        default=True,
        description="Whether to update imports across the codebase",
    )
    maintain_compatibility: bool = Field(
        default=True,
        description="Whether to maintain consistent imports across modules",
    )
    split_mode: EnumSplitMode = Field(
        default=EnumSplitMode.ONE_PER_FILE,
        description="Mode for splitting models",
    )
    preserve_comments: bool = Field(
        default=True,
        description="Whether to preserve comments and docstrings",
    )
    output_file_prefix: str = Field(
        default="model_",
        description="Prefix for generated model files",
    )


class ModelInfo(BaseModel):
    """Information about a model found in a file."""

    name: str = Field(description="Name of the model class")
    start_line: int = Field(description="Starting line number of the model")
    end_line: int = Field(description="Ending line number of the model")
    imports: list[str] = Field(description="Import statements needed by this model")
    dependencies: list[str] = Field(description="Other models this model depends on")
    base_classes: list[str] = Field(description="Base classes of the model")
    docstring: str | None = Field(
        default=None,
        description="Model docstring if present",
    )
    decorators: list[str] = Field(
        default_factory=list,
        description="Decorators applied to the model",
    )


class ModelExtractionPlan(BaseModel):
    """Plan for extracting models from a file."""

    extraction_order: list[str] = Field(
        description="Order in which models should be extracted",
    )
    common_imports: list[str] = Field(description="Imports common to all models")
    dependency_graph: dict[str, list[str]] = Field(
        description="Graph of model dependencies",
    )
    target_files: dict[str, str] = Field(
        description="Mapping of model names to target file paths",
    )
    compatibility_imports: dict[str, list[str]] = Field(
        default_factory=dict,
        description="Imports needed for consistent module references",
    )


class ModelSplitterResult(BaseModel):
    """Complete results from model splitting operation."""

    file_path: str = Field(description="Path to the analyzed file")
    models: list[ModelInfo] = Field(
        description="Information about models found in the file",
    )
    extraction_plan: ModelExtractionPlan | None = Field(
        default=None,
        description="Plan for extracting models",
    )
    files_created: list[str] = Field(
        default_factory=list,
        description="Paths to files created during split operation",
    )
    backup_path: str | None = Field(
        default=None,
        description="Path to backup file if created",
    )
    import_updates: dict[str, list[str]] = Field(
        default_factory=dict,
        description="Import updates needed across codebase",
    )
    warnings: list[str] = Field(default_factory=list, description="Warning messages")


class ModelSplitterInputState(OnexInputState):
    """Input state for model splitter tool."""

    file_path: str = Field(description="Path to the Python file to analyze or split")
    output_dir: str | None = Field(
        default=None,
        description="Directory where split model files will be created",
    )
    config: ModelSplitterConfig = Field(
        default_factory=ModelSplitterConfig,
        description="Configuration options for model splitting",
    )
    operation: str = Field(
        default="analyze",
        description="Operation to perform",
        pattern="^(analyze|split|plan)$",
    )


class ModelSplitterOutputState(OnexOutputState):
    """Output state for model splitter tool."""

    success: bool = Field(description="Whether operation completed successfully")
    operation_result: ModelSplitterResult | None = Field(
        default=None,
        description="Complete operation results",
    )
    error_message: str | None = Field(
        default=None,
        description="Error message if operation failed",
    )
    models_found: int = Field(description="Number of models found in the file")
    files_created: int = Field(
        description="Number of files created (for split operation)",
    )
    processing_time_ms: float = Field(
        description="Time taken for operation in milliseconds",
    )


def create_model_splitter_input_state(
    file_path: str,
    output_dir: str | None = None,
    config: ModelSplitterConfig | None = None,
    operation: str = "analyze",
) -> ModelSplitterInputState:
    """
    Create a model splitter input state.

    Args:
        file_path: Path to the Python file to analyze or split
        output_dir: Optional directory for split model files
        config: Optional configuration for splitting
        operation: Operation to perform (analyze, split, plan)

    Returns:
        Configured input state
    """
    return ModelSplitterInputState(
        file_path=file_path,
        output_dir=output_dir,
        config=config or ModelSplitterConfig(),
        operation=operation,
    )


def create_model_splitter_output_state(
    success: bool,
    models_found: int,
    files_created: int,
    processing_time_ms: float,
    operation_result: ModelSplitterResult | None = None,
    error_message: str | None = None,
) -> ModelSplitterOutputState:
    """
    Create a model splitter output state.

    Args:
        success: Whether operation completed successfully
        models_found: Number of models found
        files_created: Number of files created
        processing_time_ms: Time taken in milliseconds
        operation_result: Optional complete operation results
        error_message: Optional error message

    Returns:
        Configured output state
    """
    return ModelSplitterOutputState(
        success=success,
        operation_result=operation_result,
        error_message=error_message,
        models_found=models_found,
        files_created=files_created,
        processing_time_ms=processing_time_ms,
    )
