"""
Function Node Core Model.

Core function information and signature details.
Part of the ModelFunctionNode restructuring to reduce excessive string fields.
"""

from __future__ import annotations

from pathlib import Path
from uuid import UUID, uuid4

from pydantic import BaseModel, Field

from ...enums.enum_function_status import EnumFunctionStatus
from ...enums.enum_function_type import EnumFunctionType
from ...enums.enum_parameter_type import EnumParameterType
from ...enums.enum_return_type import EnumReturnType
from ..metadata.model_semver import ModelSemVer


class ModelFunctionNodeCore(BaseModel):
    """
    Core function node information.

    Contains essential function identification, signature, and status
    without documentation or performance clutter.
    """

    # Core function information - Entity reference with UUID
    function_id: UUID = Field(
        default_factory=uuid4,
        description="Unique identifier for the function entity",
    )
    function_display_name: str | None = Field(
        None,
        description="Human-readable function name",
    )
    description: str = Field(default="", description="Function description")
    function_type: EnumFunctionType = Field(
        default=EnumFunctionType.COMPUTE,
        description="Type of function (function, method, property, etc.)",
    )

    # Function signature
    parameters: list[str] = Field(
        default_factory=list,
        description="Function parameters",
    )
    return_type: EnumReturnType | None = Field(
        default=None,
        description="Function return type annotation",
    )
    parameter_types: dict[str, EnumParameterType] = Field(
        default_factory=dict,
        description="Parameter type annotations",
    )

    # Status and versioning
    status: EnumFunctionStatus = Field(
        default=EnumFunctionStatus.ACTIVE,
        description="Function status (active, deprecated, disabled)",
    )
    version: ModelSemVer = Field(
        default_factory=lambda: ModelSemVer(major=1, minor=0, patch=0),
        description="Function version",
    )

    # Location information
    module: str | None = Field(
        default=None,
        description="Module containing the function",
    )
    file_path: Path | None = Field(default=None, description="Source file path")
    line_number: int | None = Field(
        default=None,
        description="Line number in source file",
        ge=1,
    )

    def is_active(self) -> bool:
        """Check if function is active."""
        return self.status == EnumFunctionStatus.ACTIVE

    def is_disabled(self) -> bool:
        """Check if function is disabled."""
        return self.status == EnumFunctionStatus.DISABLED

    def is_deprecated(self) -> bool:
        """Check if function is deprecated."""
        return self.status == EnumFunctionStatus.DEPRECATED

    def get_parameter_count(self) -> int:
        """Get number of parameters."""
        return len(self.parameters)

    def has_type_annotations(self) -> bool:
        """Check if function has type annotations."""
        return bool(self.return_type or self.parameter_types)

    def get_full_name(self) -> str:
        """Get full qualified function name."""
        function_name = (
            self.function_display_name or f"function_{str(self.function_id)[:8]}"
        )
        if self.module:
            return f"{self.module}.{function_name}"
        return function_name

    def has_location_info(self) -> bool:
        """Check if location information is available."""
        return bool(self.file_path and self.line_number)

    @classmethod
    def create_simple(
        cls,
        name: str,
        description: str = "",
        function_type: EnumFunctionType = EnumFunctionType.COMPUTE,
    ) -> ModelFunctionNodeCore:
        """Create a simple function core."""
        import hashlib

        # Generate UUID from function name
        function_hash = hashlib.sha256(name.encode()).hexdigest()
        function_id = UUID(
            f"{function_hash[:8]}-{function_hash[8:12]}-{function_hash[12:16]}-{function_hash[16:20]}-{function_hash[20:32]}",
        )

        return cls(
            function_id=function_id,
            function_display_name=name,
            description=description,
            function_type=function_type,
        )

    @classmethod
    def create_from_signature(
        cls,
        name: str,
        parameters: list[str],
        return_type: EnumReturnType | None = None,
        description: str = "",
    ) -> ModelFunctionNodeCore:
        """Create function core from signature information."""
        import hashlib

        # Generate UUID from function name
        function_hash = hashlib.sha256(name.encode()).hexdigest()
        function_id = UUID(
            f"{function_hash[:8]}-{function_hash[8:12]}-{function_hash[12:16]}-{function_hash[16:20]}-{function_hash[20:32]}",
        )

        return cls(
            function_id=function_id,
            function_display_name=name,
            description=description,
            parameters=parameters,
            return_type=return_type,
        )

    @property
    def name(self) -> str:
        """Get function name."""
        return self.function_display_name or f"function_{str(self.function_id)[:8]}"

    @property
    def function_name(self) -> str:
        """Get function name."""
        return self.function_display_name or f"function_{str(self.function_id)[:8]}"


# Export for use
__all__ = ["ModelFunctionNodeCore"]
