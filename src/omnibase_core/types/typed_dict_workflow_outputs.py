"""
TypedDict for workflow outputs dictionary representation.

Used by ModelWorkflowOutputs.to_dict() method.
"""

from typing import NotRequired, TypedDict


class TypedDictWorkflowOutputsDict(TypedDict, total=True):
    """
    TypedDict for workflow outputs dictionary.

    Used for ModelWorkflowOutputs.to_dict() return type.

    All fields are optional since None values are filtered out during conversion.
    The method also merges custom_outputs fields into the result.

    Attributes:
        result: Main result value
        status_message: Human-readable status message
        error_message: Error message if failed
        generated_files: List of generated file paths
        modified_files: List of modified file paths
        execution_time_ms: Execution time in milliseconds
        items_processed: Number of items processed
        success_count: Number of successful operations
        failure_count: Number of failed operations
        data: Structured data outputs
    """

    result: NotRequired[str]
    status_message: NotRequired[str]
    error_message: NotRequired[str]
    generated_files: NotRequired[list[str]]
    modified_files: NotRequired[list[str]]
    execution_time_ms: NotRequired[int]
    items_processed: NotRequired[int]
    success_count: NotRequired[int]
    failure_count: NotRequired[int]
    data: NotRequired[
        dict[str, str | int | float | bool | None | list[object] | dict[str, object]]
    ]


__all__ = ["TypedDictWorkflowOutputsDict"]
