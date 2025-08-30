"""
Protocol for AST Builder functionality.

Defines the interface for building Python Abstract Syntax Tree (AST)
nodes for code generation.
"""

import ast
from typing import List, Optional, Protocol, Union

from omnibase_core.decorators import allow_any_type
from omnibase_core.model.core.model_schema import ModelSchema


class ProtocolASTBuilder(Protocol):
    """Protocol for AST building functionality.

    This protocol defines the interface for generating Python AST
    nodes from schema definitions, used in code generation tools.
    """

    def generate_model_class(
        self, class_name: str, schema: ModelSchema, base_class: str = "BaseModel"
    ) -> ast.ClassDef:
        """Generate a Pydantic model class from a schema definition.

        Args:
            class_name: Name for the generated class
            schema: Schema definition to convert
            base_class: Base class to inherit from

        Returns:
            AST ClassDef node for the model
        """
        ...

    def generate_model_field(
        self, field_name: str, field_schema: ModelSchema, required: bool = True
    ) -> ast.AnnAssign:
        """Generate a model field annotation.

        Args:
            field_name: Name of the field
            field_schema: Schema for the field
            required: Whether field is required

        Returns:
            AST annotation assignment for the field
        """
        ...

    def generate_enum_class(
        self, class_name: str, enum_values: List[str]
    ) -> ast.ClassDef:
        """Generate an enum class from values.

        Args:
            class_name: Name for the enum class
            enum_values: List of enum values

        Returns:
            AST ClassDef node for the enum
        """
        ...

    def generate_import_statement(
        self, module: str, names: List[str], alias: Optional[str] = None
    ) -> ast.ImportFrom:
        """Generate an import statement.

        Args:
            module: Module to import from
            names: Names to import
            alias: Optional alias for import

        Returns:
            AST ImportFrom node
        """
        ...

    def generate_docstring(self, text: str) -> ast.Expr:
        """Generate a docstring node.

        Args:
            text: Docstring text

        Returns:
            AST Expr node containing docstring
        """
        ...

    @allow_any_type(
        "Field default values can be any Python value - strings, numbers, functions, etc."
    )
    def generate_field_default(self, default_value) -> ast.expr:
        """Generate default value expression for a field.

        Args:
            default_value: Default value (any Python value)

        Returns:
            AST expression for the default
        """
        ...

    def generate_validator_method(
        self, field_name: str, validator_type: str = "field_validator"
    ) -> ast.FunctionDef:
        """Generate a Pydantic validator method.

        Args:
            field_name: Field to validate
            validator_type: Type of validator

        Returns:
            AST FunctionDef for validator
        """
        ...

    def generate_type_annotation(
        self, type_string: str
    ) -> Union[ast.Name, ast.Subscript]:
        """Generate type annotation from string.

        Args:
            type_string: Type as string

        Returns:
            AST node for type annotation
        """
        ...

    def generate_module(
        self,
        imports: List[ast.ImportFrom],
        classes: List[ast.ClassDef],
        module_docstring: Optional[str] = None,
    ) -> ast.Module:
        """Generate complete module AST.

        Args:
            imports: Import statements
            classes: Class definitions
            module_docstring: Optional module docstring

        Returns:
            Complete AST Module node
        """
        ...
