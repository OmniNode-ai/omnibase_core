import builtins
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field

from omnibase_core.enums.enum_function_language import EnumFunctionLanguage
from omnibase_core.enums.enum_tool_type import EnumToolType

# Add other tool types as needed


# Add other languages as needed


class ModelFunctionTool(BaseModel):
    """
    Language-agnostic function tool metadata for the unified tools approach.
    Functions are treated as tools within the main metadata block.
    """

    type: EnumToolType = Field(
        default=EnumToolType.FUNCTION,
        description="Tool type (always 'function')",
    )
    language: EnumFunctionLanguage = Field(
        default=...,
        description="Programming language (python, javascript, typescript, bash, yaml, etc.)",
    )
    line: int = Field(default=..., description="Line number where function is defined")
    description: str = Field(default=..., description="Function description")
    inputs: list[str] = Field(
        default_factory=list,
        description="Function input parameters with types",
    )
    outputs: list[str] = Field(
        default_factory=list,
        description="Function output types",
    )
    error_codes: list[str] = Field(
        default_factory=list,
        description="Error codes this function may raise",
    )
    side_effects: list[str] = Field(
        default_factory=list,
        description="Side effects this function may have",
    )

    def to_serializable_dict(self) -> dict[str, Any]:
        return {k: getattr(self, k) for k in self.__class__.model_fields}

    @classmethod
    def from_serializable_dict(
        cls: builtins.type["ModelFunctionTool"],
        data: dict[str, Any],
    ) -> "ModelFunctionTool":
        return cls(**data)
