from enum import Enum
from typing import List, Type

from pydantic import BaseModel, Field


class ToolTypeEnum(str, Enum):
    FUNCTION = "function"
    # Add other tool types as needed


class FunctionLanguageEnum(str, Enum):
    PYTHON = "python"
    JAVASCRIPT = "javascript"
    TYPESCRIPT = "typescript"
    BASH = "bash"
    YAML = "yaml"
    # Add other languages as needed


class ModelFunctionTool(BaseModel):
    """
    Language-agnostic function tool metadata for the unified tools approach.
    Functions are treated as tools within the main metadata block.
    """

    type: ToolTypeEnum = Field(
        default=ToolTypeEnum.FUNCTION, description="Tool type (always 'function')"
    )
    language: FunctionLanguageEnum = Field(
        ...,
        description="Programming language (python, javascript, typescript, bash, yaml, etc.)",
    )
    line: int = Field(..., description="Line number where function is defined")
    description: str = Field(..., description="Function description")
    inputs: List[str] = Field(
        default_factory=list, description="Function input parameters with types"
    )
    outputs: List[str] = Field(
        default_factory=list, description="Function output types"
    )
    error_codes: List[str] = Field(
        default_factory=list, description="Error codes this function may raise"
    )
    side_effects: List[str] = Field(
        default_factory=list, description="Side effects this function may have"
    )

    def to_serializable_dict(self) -> dict:
        return {k: getattr(self, k) for k in self.__class__.model_fields}

    @classmethod
    def from_serializable_dict(
        cls: Type["ModelFunctionTool"], data: dict
    ) -> "ModelFunctionTool":
        return cls(**data)
