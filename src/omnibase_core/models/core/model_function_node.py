import builtins
from enum import Enum

from pydantic import BaseModel, Field


class NodeTypeEnum(str, Enum):
    FUNCTION = "function"
    # Add other node types as needed


class FunctionLanguageEnum(str, Enum):
    PYTHON = "python"
    JAVASCRIPT = "javascript"
    TYPESCRIPT = "typescript"
    BASH = "bash"
    YAML = "yaml"
    # Add other languages as needed


class ModelFunctionNode(BaseModel):
    """
    Language-agnostic function node metadata for the unified nodes approach.
    Functions are treated as nodes within the main metadata block.
    """

    type: NodeTypeEnum = Field(
        default=NodeTypeEnum.FUNCTION,
        description="Node type (always 'function')",
    )
    language: FunctionLanguageEnum = Field(
        ...,
        description="Programming language (python, javascript, typescript, bash, yaml, etc.)",
    )
    line: int = Field(..., description="Line number where function is defined")
    description: str = Field(..., description="Function description")
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

    def to_serializable_dict(self) -> dict:
        return {k: getattr(self, k) for k in self.__class__.model_fields}

    @classmethod
    def from_serializable_dict(
        cls: builtins.type["ModelFunctionNode"],
        data: dict,
    ) -> "ModelFunctionNode":
        return cls(**data)
