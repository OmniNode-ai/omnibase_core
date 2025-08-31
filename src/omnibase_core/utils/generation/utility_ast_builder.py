"""
AST Builder Utility for ONEX Contract Generation.

Handles generation of Python AST nodes for Pydantic models, enums, and fields.
Provides consistent AST generation across all ONEX tools.
"""

import ast

from omnibase_core.core.core_structured_logging import (
    emit_log_event_sync as emit_log_event,
)
from omnibase_core.enums.enum_log_level import EnumLogLevel as LogLevel
from omnibase_core.model.core.model_schema import ModelSchema


class UtilityASTBuilder:
    """
    Utility for building Python AST nodes from schemas.

    Handles:
    - Pydantic model class generation
    - Field definitions with type annotations
    - Field() calls with constraints
    - Enum class generation
    - Type annotation AST nodes
    """

    def __init__(self, type_mapper=None, reference_resolver=None):
        """
        Initialize the AST builder.

        Args:
            type_mapper: Type mapper utility for type string generation
            reference_resolver: Reference resolver for handling $refs
        """
        self.type_mapper = type_mapper
        self.reference_resolver = reference_resolver

    def generate_model_class(
        self,
        class_name: str,
        schema: ModelSchema,
        base_class: str = "BaseModel",
    ) -> ast.ClassDef:
        """
        Generate a Pydantic model class from a schema definition.

        Args:
            class_name: Name of the generated class
            schema: Schema definition
            base_class: Base class name (default: "BaseModel")

        Returns:
            AST ClassDef node for the model
        """
        # DEBUG LOGGING: Track where this is being called from
        import traceback

        from omnibase_core.core.core_structured_logging import (
            emit_log_event_sync as emit_log_event,
        )
        from omnibase_core.enums.enum_log_level import EnumLogLevel as LogLevel

        emit_log_event(
            LogLevel.DEBUG,
            f"🚨 DEBUG: UtilityASTBuilder.generate_model_class called for: {class_name}",
            {
                "class_name": class_name,
                "schema_type": getattr(schema, "schema_type", "UNKNOWN"),
                "has_properties": bool(getattr(schema, "properties", None)),
                "has_enum_values": bool(getattr(schema, "enum_values", None)),
                "call_stack": traceback.format_stack()[-2].strip(),
            },
        )
        # Create base class reference
        bases = [ast.Name(id=base_class, ctx=ast.Load())]

        # Create class body
        body = []

        # Add docstring
        docstring = f'"{class_name} from contract definition."'
        docstring_node = ast.Expr(value=ast.Constant(value=docstring))
        body.append(docstring_node)

        # Generate fields from properties
        if schema.properties:
            required_fields = schema.required or []
            for field_name, field_schema in schema.properties.items():
                is_required = field_name in required_fields
                field_def = self.create_field_definition(
                    field_name,
                    field_schema,
                    is_required,
                )
                if field_def:
                    body.append(field_def)

        # If no fields were added, add a pass statement
        if len(body) == 1:  # Only docstring
            emit_log_event(
                LogLevel.DEBUG,
                f"🚨 DEBUG: Adding pass statement to empty model class: {class_name}",
                {
                    "class_name": class_name,
                    "base_class": base_class,
                    "reason": "No properties found in schema - creating empty BaseModel with pass",
                },
            )
            body.append(ast.Pass())

        return ast.ClassDef(
            name=class_name,
            bases=bases,
            keywords=[],
            decorator_list=[],
            body=body,
        )

    def create_field_definition(
        self,
        field_name: str,
        field_schema: ModelSchema,
        is_required: bool = True,
    ) -> ast.AnnAssign | None:
        """
        Create a field definition from schema.

        Args:
            field_name: Name of the field
            field_schema: Schema for the field
            is_required: Whether the field is required

        Returns:
            AST AnnAssign node for the field definition
        """
        # Debug logging for datetime fields
        if field_name in ["start_time", "end_time"]:
            emit_log_event(
                LogLevel.INFO,
                f"Creating field definition for {field_name}",
                {
                    "field_name": field_name,
                    "schema_type": field_schema.schema_type if field_schema else None,
                    "format": getattr(field_schema, "format", None),
                    "is_required": is_required,
                },
            )

        # Get type annotation
        type_annotation = self.get_type_annotation(field_schema)

        # Ensure type_annotation is an AST node
        if not isinstance(type_annotation, ast.expr):
            emit_log_event(
                LogLevel.ERROR,
                f"Type annotation is not an AST expr: {type(type_annotation)} for field {field_name}",
                {"field_name": field_name, "type": str(type(type_annotation))},
            )
            # Fallback to Any
            type_annotation = ast.Name(id="Any", ctx=ast.Load())

        # Create Field() call
        field_call = self.create_field_call(field_schema, is_required)

        # Create the assignment
        target = ast.Name(id=field_name, ctx=ast.Store())

        return ast.AnnAssign(
            target=target,
            annotation=type_annotation,
            value=field_call,
            simple=1,
        )

    def get_type_annotation(self, schema: ModelSchema) -> ast.expr:
        """
        Get proper type annotation from schema.

        Args:
            schema: Schema to generate type annotation for

        Returns:
            AST expression node for the type annotation
        """
        # Get schema type
        schema_type = schema.schema_type

        # Handle $ref references
        if schema.ref:
            if self.reference_resolver:
                ref_name = self.reference_resolver.resolve_ref(schema.ref)
            else:
                # Fallback resolution
                ref_name = schema.ref.split("/")[-1]
                if not ref_name.startswith("Model"):
                    ref_name = f"Model{ref_name}"
            return ast.Name(id=ref_name, ctx=ast.Load())

        # Handle enums
        if schema_type == "string" and schema.enum_values:
            if self.type_mapper:
                enum_name = self.type_mapper.generate_enum_name_from_values(
                    schema.enum_values,
                )
            else:
                # Fallback enum name generation
                first_value = schema.enum_values[0] if schema.enum_values else "Generic"
                # Replace hyphens with underscores for valid Python identifiers
                clean_value = first_value.replace("-", "_")
                # Handle snake_case values (including those that had hyphens)
                if "_" in clean_value:
                    parts = clean_value.split("_")
                    enum_name = "Enum" + "".join(word.capitalize() for word in parts)
                else:
                    enum_name = f"Enum{clean_value.capitalize()}"
            return ast.Name(id=enum_name, ctx=ast.Load())

        # Handle array type
        if schema_type == "array":
            if self.type_mapper:
                array_type_str = self.type_mapper.get_array_type_string(schema)
            else:
                # Fallback array type
                array_type_str = "List[Any]"

            # For List[X], we need to create a subscript AST node
            if array_type_str.startswith("List["):
                # Extract the inner type
                inner_type = array_type_str[5:-1]  # Remove "List[" and "]"
                return ast.Subscript(
                    value=ast.Name(id="List", ctx=ast.Load()),
                    slice=ast.Name(id=inner_type, ctx=ast.Load()),
                    ctx=ast.Load(),
                )
            return ast.Name(id=array_type_str, ctx=ast.Load())

        # Handle object type
        if schema_type == "object":
            if self.type_mapper:
                object_type_str = self.type_mapper.get_object_type_string(schema)
            else:
                # ONEX COMPLIANCE: Always use structured types instead of Dict[str, Any]
                object_type_str = "ModelObjectData"

            # For structured object types, return simple Name node
            if object_type_str in ["ModelObjectData", "ModelSchemaValue"]:
                return ast.Name(id=object_type_str, ctx=ast.Load())

            # For other dict types, parse the type string properly
            if object_type_str.startswith("Dict["):
                # Parse "Dict[str, Any]" or "Dict[str, int]" properly
                import re

                match = re.match(r"Dict\[([^,]+),\s*([^\]]+)\]", object_type_str)
                if match:
                    key_type = match.group(1).strip()
                    value_type = match.group(2).strip()
                    return ast.Subscript(
                        value=ast.Name(id="Dict", ctx=ast.Load()),
                        slice=ast.Tuple(
                            elts=[
                                ast.Name(id=key_type, ctx=ast.Load()),
                                ast.Name(id=value_type, ctx=ast.Load()),
                            ],
                            ctx=ast.Load(),
                        ),
                        ctx=ast.Load(),
                    )
                # Fallback to generic dict
                return ast.Subscript(
                    value=ast.Name(id="Dict", ctx=ast.Load()),
                    slice=ast.Tuple(
                        elts=[
                            ast.Name(id="str", ctx=ast.Load()),
                            ast.Name(id="Any", ctx=ast.Load()),
                        ],
                        ctx=ast.Load(),
                    ),
                    ctx=ast.Load(),
                )
            return ast.Name(id=object_type_str, ctx=ast.Load())

        # Handle string with format using type mapper if available
        if schema_type == "string" and self.type_mapper:
            emit_log_event(
                LogLevel.INFO,
                "AST builder checking string field with type mapper",
                {"schema_type": schema_type, "format": getattr(schema, "format", None)},
            )
            # Let type mapper handle format detection
            type_str = self.type_mapper.get_type_string_from_schema(schema)
            emit_log_event(
                LogLevel.INFO,
                f"Type mapper returned: {type_str}",
                {"type_str": type_str, "is_special": type_str != "str"},
            )
            if type_str != "str":  # Type mapper found a special format
                return ast.Name(id=type_str, ctx=ast.Load())

        # Handle basic types
        type_mapping = {
            "string": "str",
            "integer": "int",
            "number": "float",
            "boolean": "bool",
        }

        mapped_type = type_mapping.get(schema_type, "Any")
        return ast.Name(id=mapped_type, ctx=ast.Load())

    def create_field_call(self, schema: ModelSchema, is_required: bool) -> ast.Call:
        """
        Create Field() call for Pydantic field.

        Args:
            schema: Schema for the field
            is_required: Whether the field is required

        Returns:
            AST Call node for Field() with appropriate arguments
        """
        args = []
        keywords = []

        # Handle required/optional fields
        if is_required:
            # Required field - use ... as first argument
            args.append(ast.Constant(value=...))
        else:
            # Optional field - use None as default
            keywords.append(ast.keyword(arg="default", value=ast.Constant(value=None)))

        # Add description if available
        if schema.description:
            keywords.append(
                ast.keyword(
                    arg="description",
                    value=ast.Constant(value=schema.description),
                ),
            )

        # Add other constraints
        if schema.minimum is not None:
            keywords.append(
                ast.keyword(arg="ge", value=ast.Constant(value=schema.minimum)),
            )
        if schema.maximum is not None:
            keywords.append(
                ast.keyword(arg="le", value=ast.Constant(value=schema.maximum)),
            )

        # Add string constraints
        if schema.min_length is not None:
            keywords.append(
                ast.keyword(
                    arg="min_length",
                    value=ast.Constant(value=schema.min_length),
                ),
            )
        if schema.max_length is not None:
            keywords.append(
                ast.keyword(
                    arg="max_length",
                    value=ast.Constant(value=schema.max_length),
                ),
            )

        # Add pattern constraint
        if schema.pattern:
            keywords.append(
                ast.keyword(arg="pattern", value=ast.Constant(value=schema.pattern)),
            )

        return ast.Call(
            func=ast.Name(id="Field", ctx=ast.Load()),
            args=args,
            keywords=keywords,
        )

    def generate_enum_class(
        self,
        class_name: str,
        enum_values: list[str],
    ) -> ast.ClassDef:
        """
        Create an enum class from enum values.

        Args:
            class_name: Name of the enum class
            enum_values: List of enum values

        Returns:
            AST ClassDef node for the enum
        """
        # Create class with str and Enum as bases
        bases = [
            ast.Name(id="str", ctx=ast.Load()),
            ast.Name(id="Enum", ctx=ast.Load()),
        ]

        body = []

        # Add docstring
        docstring = f"{class_name} enumeration from contract definitions."
        body.append(ast.Expr(value=ast.Constant(value=docstring)))

        # Add enum values
        for enum_value in enum_values:
            attr_name = enum_value.upper().replace("-", "_").replace(" ", "_")
            assignment = ast.Assign(
                targets=[ast.Name(id=attr_name, ctx=ast.Store())],
                value=ast.Constant(value=enum_value),
            )
            body.append(assignment)

        # If no values, add pass
        if len(body) == 1:  # Only docstring
            body.append(ast.Pass())

        class_def = ast.ClassDef(
            name=class_name,
            bases=bases,
            keywords=[],
            decorator_list=[],
            body=body,
        )

        # Fix missing locations
        ast.fix_missing_locations(class_def)
        return class_def

    def generate_import_statement(
        self,
        module: str,
        names: list[str],
    ) -> ast.ImportFrom:
        """
        Generate an import statement.

        Args:
            module: Module name to import from
            names: List of names to import

        Returns:
            AST ImportFrom node
        """
        aliases = [ast.alias(name=name, asname=None) for name in names]
        return ast.ImportFrom(module=module, names=aliases, level=0)

    def generate_module_with_imports(
        self,
        classes: list[ast.ClassDef],
        imports: dict[str, list[str]],
    ) -> ast.Module:
        """
        Generate a complete module with imports and classes.

        Args:
            classes: List of class definitions
            imports: Dict mapping module names to import lists

        Returns:
            AST Module node with imports and classes
        """
        body = []

        # Add imports
        for module, names in imports.items():
            import_stmt = self.generate_import_statement(module, names)
            body.append(import_stmt)

        # Add blank line after imports if there are any
        # NOTE: We don't add blank lines in AST - ast.unparse handles formatting

        # Add classes
        body.extend(classes)

        return ast.Module(body=body, type_ignores=[])

    def unparse_node(self, node: ast.AST) -> str:
        """
        Convert an AST node back to source code.

        Args:
            node: AST node to unparse

        Returns:
            Source code string
        """
        try:
            # Fix missing locations before unparsing
            ast.fix_missing_locations(node)
            return ast.unparse(node)
        except Exception as e:
            emit_log_event(
                LogLevel.ERROR,
                f"Failed to unparse AST node: {e}",
                {"node_type": type(node).__name__},
            )
            return f"# Failed to generate code: {e}"
