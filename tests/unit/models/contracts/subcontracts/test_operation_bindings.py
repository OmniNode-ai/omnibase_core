"""
Tests for operation bindings DSL models (OMN-1410).

Tests the operation bindings subcontract models including:
- EnumBindingFunction - allowed pipe functions
- ModelBindingExpression - expression validation and parsing
- ModelEnvelopeTemplate - envelope template construction
- ModelResponseMapping - response field mapping
- ModelOperationMapping - combined envelope and response
- ModelOperationBindings - top-level subcontract

Security tests verify that template injection attacks are blocked via:
- Denied builtins (eval, __class__, etc.)
- Double underscore blocking
- Bracket notation rejection
- Ternary operator rejection
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from omnibase_core.enums.enum_binding_function import EnumBindingFunction
from omnibase_core.models.contracts.subcontracts.model_binding_expression import (
    ModelBindingExpression,
)
from omnibase_core.models.contracts.subcontracts.model_envelope_template import (
    ModelEnvelopeTemplate,
)
from omnibase_core.models.contracts.subcontracts.model_operation_bindings import (
    ModelOperationBindings,
)
from omnibase_core.models.contracts.subcontracts.model_operation_mapping import (
    ModelOperationMapping,
)
from omnibase_core.models.contracts.subcontracts.model_response_mapping import (
    ModelResponseMapping,
)
from omnibase_core.models.errors.model_onex_error import ModelOnexError
from omnibase_core.models.primitives.model_semver import ModelSemVer

# Default version for test instances
DEFAULT_VERSION = ModelSemVer(major=1, minor=0, patch=0)


# =============================================================================
# EnumBindingFunction Tests
# =============================================================================


@pytest.mark.unit
@pytest.mark.timeout(60)
class TestEnumBindingFunction:
    """Tests for EnumBindingFunction enum."""

    def test_enum_values_correct(self) -> None:
        """Test that enum values are correctly defined."""
        assert EnumBindingFunction.TO_JSON.value == "to_json"
        assert EnumBindingFunction.FROM_JSON.value == "from_json"

    def test_str_conversion_via_str_value_helper(self) -> None:
        """Test string conversion returns the value (via StrValueHelper)."""
        assert str(EnumBindingFunction.TO_JSON) == "to_json"
        assert str(EnumBindingFunction.FROM_JSON) == "from_json"

    def test_enum_member_count(self) -> None:
        """Test that only expected members exist."""
        members = list(EnumBindingFunction)
        assert len(members) == 2
        assert EnumBindingFunction.TO_JSON in members
        assert EnumBindingFunction.FROM_JSON in members

    def test_enum_from_string_value(self) -> None:
        """Test creating enum from string value."""
        assert EnumBindingFunction("to_json") == EnumBindingFunction.TO_JSON
        assert EnumBindingFunction("from_json") == EnumBindingFunction.FROM_JSON

    def test_enum_invalid_value_raises(self) -> None:
        """Test that invalid string value raises ValueError."""
        with pytest.raises(ValueError):
            EnumBindingFunction("invalid_function")


# =============================================================================
# ModelBindingExpression Tests
# =============================================================================


@pytest.mark.unit
@pytest.mark.timeout(60)
class TestModelBindingExpressionValid:
    """Tests for valid ModelBindingExpression patterns."""

    def test_simple_request_field(self) -> None:
        """Test simple request field access."""
        expr = ModelBindingExpression(raw="${request.field}")
        assert expr.root == "request"
        assert expr.path == "field"
        assert expr.function is None
        assert expr.full_path == "request.field"

    def test_nested_request_path(self) -> None:
        """Test nested path access."""
        expr = ModelBindingExpression(raw="${request.nested.path}")
        assert expr.root == "request"
        assert expr.path == "nested.path"
        assert expr.function is None

    def test_result_root(self) -> None:
        """Test result root access."""
        expr = ModelBindingExpression(raw="${result.data}")
        assert expr.root == "result"
        assert expr.path == "data"

    def test_binding_config_root(self) -> None:
        """Test binding.config root access."""
        expr = ModelBindingExpression(raw="${binding.config.base_path}")
        assert expr.root == "binding.config"
        assert expr.path == "base_path"

    def test_contract_config_root(self) -> None:
        """Test contract.config root access."""
        expr = ModelBindingExpression(raw="${contract.config.value}")
        assert expr.root == "contract.config"
        assert expr.path == "value"

    def test_with_to_json_function(self) -> None:
        """Test expression with to_json pipe function."""
        expr = ModelBindingExpression(raw="${request.snapshot | to_json}")
        assert expr.root == "request"
        assert expr.path == "snapshot"
        assert expr.function == EnumBindingFunction.TO_JSON

    def test_with_from_json_function(self) -> None:
        """Test expression with from_json pipe function."""
        expr = ModelBindingExpression(raw="${result.data | from_json}")
        assert expr.root == "result"
        assert expr.path == "data"
        assert expr.function == EnumBindingFunction.FROM_JSON

    def test_root_without_path(self) -> None:
        """Test expression with just root (no additional path)."""
        expr = ModelBindingExpression(raw="${request}")
        assert expr.root == "request"
        assert expr.path is None
        assert expr.full_path == "request"

    def test_root_only_with_function(self) -> None:
        """Test root-only expression with function."""
        expr = ModelBindingExpression(raw="${result | to_json}")
        assert expr.root == "result"
        assert expr.path is None
        assert expr.function == EnumBindingFunction.TO_JSON

    def test_deeply_nested_path(self) -> None:
        """Test deeply nested path access."""
        expr = ModelBindingExpression(raw="${request.a.b.c.d.e}")
        assert expr.root == "request"
        assert expr.path == "a.b.c.d.e"
        assert expr.full_path == "request.a.b.c.d.e"

    def test_path_with_underscores(self) -> None:
        """Test path with underscores in field names."""
        expr = ModelBindingExpression(raw="${request.snake_case_field}")
        assert expr.path == "snake_case_field"

    def test_path_with_numbers(self) -> None:
        """Test path with numbers in field names."""
        expr = ModelBindingExpression(raw="${request.field1.item2}")
        assert expr.path == "field1.item2"

    def test_whitespace_around_pipe(self) -> None:
        """Test that whitespace around pipe is handled."""
        expr = ModelBindingExpression(raw="${request.data    |    to_json}")
        assert expr.function == EnumBindingFunction.TO_JSON


@pytest.mark.unit
@pytest.mark.timeout(60)
class TestModelBindingExpressionInvalid:
    """Tests for invalid ModelBindingExpression patterns."""

    def test_ambiguous_config_root(self) -> None:
        """Test that ambiguous 'config' root is rejected with helpful message."""
        with pytest.raises(ModelOnexError) as exc_info:
            ModelBindingExpression(raw="${config.x}")
        assert "Ambiguous root" in str(exc_info.value)
        assert "binding.config" in str(exc_info.value)
        assert "contract.config" in str(exc_info.value)

    def test_disallowed_env_root(self) -> None:
        """Test that 'env' root is rejected."""
        with pytest.raises(ModelOnexError) as exc_info:
            ModelBindingExpression(raw="${env.VAR}")
        assert "Invalid binding expression format" in str(exc_info.value)

    def test_unknown_pipe_function(self) -> None:
        """Test that unknown pipe function is rejected."""
        with pytest.raises(ModelOnexError) as exc_info:
            ModelBindingExpression(raw="${request.x | unknown}")
        assert "Invalid binding expression format" in str(exc_info.value)

    def test_chained_pipes_rejected(self) -> None:
        """Test that chained pipes are rejected."""
        with pytest.raises(ModelOnexError) as exc_info:
            ModelBindingExpression(raw="${request.x | to_json | from_json}")
        assert "Chained pipes not allowed" in str(exc_info.value)

    def test_ternary_operator_rejected(self) -> None:
        """Test that ternary operators are rejected."""
        with pytest.raises(ModelOnexError) as exc_info:
            ModelBindingExpression(raw="${result.success ? 'a' : 'b'}")
        assert "Ternary operators not allowed" in str(exc_info.value)

    def test_security_double_underscore_rejected(self) -> None:
        """Test that double underscore in path is rejected (security)."""
        with pytest.raises(ModelOnexError) as exc_info:
            ModelBindingExpression(raw="${request.__dict__}")
        # __dict__ is caught by denied builtins check
        assert "Security violation" in str(exc_info.value)
        assert "__dict__" in str(exc_info.value)

    def test_security_double_underscore_custom_rejected(self) -> None:
        """Test that custom double underscore pattern is rejected."""
        with pytest.raises(ModelOnexError) as exc_info:
            ModelBindingExpression(raw="${request.my__custom__field}")
        assert "Security violation" in str(exc_info.value)
        assert "double underscore" in str(exc_info.value)

    def test_security_class_attribute_rejected(self) -> None:
        """Test that __class__ is rejected via denied builtins."""
        with pytest.raises(ModelOnexError) as exc_info:
            ModelBindingExpression(raw="${request.__class__}")
        # Either double underscore check or denied builtin check will catch this
        assert "Security violation" in str(exc_info.value)

    def test_bracket_notation_rejected(self) -> None:
        """Test that bracket notation is rejected."""
        with pytest.raises(ModelOnexError) as exc_info:
            ModelBindingExpression(raw="${request.items[0]}")
        assert "Bracket notation not allowed" in str(exc_info.value)

    def test_empty_expression_rejected(self) -> None:
        """Test that empty expression is rejected."""
        with pytest.raises(ModelOnexError) as exc_info:
            ModelBindingExpression(raw="")
        assert "cannot be empty" in str(exc_info.value)

    def test_non_string_rejected(self) -> None:
        """Test that non-string value is rejected."""
        with pytest.raises(ModelOnexError) as exc_info:
            ModelBindingExpression(raw=123)
        assert "must be a string" in str(exc_info.value)

    def test_missing_dollar_brace(self) -> None:
        """Test that expression without ${} is rejected."""
        with pytest.raises(ModelOnexError) as exc_info:
            ModelBindingExpression(raw="request.field")
        assert "Invalid binding expression format" in str(exc_info.value)

    def test_invalid_root(self) -> None:
        """Test that invalid root is rejected."""
        with pytest.raises(ModelOnexError) as exc_info:
            ModelBindingExpression(raw="${unknown.field}")
        assert "Invalid binding expression format" in str(exc_info.value)

    def test_security_eval_rejected(self) -> None:
        """Test that eval in path is rejected via denied builtins."""
        with pytest.raises(ModelOnexError) as exc_info:
            ModelBindingExpression(raw="${request.eval}")
        assert "Security violation" in str(exc_info.value)
        assert "eval" in str(exc_info.value)

    def test_security_import_rejected(self) -> None:
        """Test that import in path is rejected via denied builtins."""
        with pytest.raises(ModelOnexError) as exc_info:
            ModelBindingExpression(raw="${request.import}")
        # Will be caught by pattern or denied builtins
        assert "Invalid binding expression format" in str(
            exc_info.value
        ) or "Security violation" in str(exc_info.value)


@pytest.mark.unit
@pytest.mark.timeout(60)
class TestModelBindingExpressionProperties:
    """Tests for ModelBindingExpression computed properties."""

    def test_repr_output(self) -> None:
        """Test __repr__ output format."""
        expr = ModelBindingExpression(raw="${request.field}")
        repr_str = repr(expr)
        assert "ModelBindingExpression" in repr_str
        assert "${request.field}" in repr_str

    def test_str_returns_raw(self) -> None:
        """Test __str__ returns raw expression."""
        raw = "${request.snapshot | to_json}"
        expr = ModelBindingExpression(raw=raw)
        assert str(expr) == raw

    def test_full_path_with_nested(self) -> None:
        """Test full_path property with nested path."""
        expr = ModelBindingExpression(raw="${binding.config.paths.output}")
        assert expr.full_path == "binding.config.paths.output"

    def test_model_is_frozen(self) -> None:
        """Test that model is immutable (frozen)."""
        expr = ModelBindingExpression(raw="${request.field}")
        with pytest.raises(ValidationError):
            expr.raw = "${request.other}"


# =============================================================================
# ModelEnvelopeTemplate Tests
# =============================================================================


@pytest.mark.unit
@pytest.mark.timeout(60)
class TestModelEnvelopeTemplateValid:
    """Tests for valid ModelEnvelopeTemplate patterns."""

    def test_basic_template(self) -> None:
        """Test basic envelope template creation."""
        template = ModelEnvelopeTemplate(
            operation="write_file",
            fields={"path": "/data/output.json", "mode": "w"},
        )
        assert template.operation == "write_file"
        assert template.fields["path"] == "/data/output.json"
        assert template.fields["mode"] == "w"

    def test_template_with_expressions(self) -> None:
        """Test template with expression fields."""
        template = ModelEnvelopeTemplate(
            operation="write_file",
            fields={
                "path": "${binding.config.base_path}/output.json",
                "content": "${request.data | to_json}",
            },
        )
        assert "${binding.config.base_path}" in template.fields["path"]

    def test_template_with_nested_dict(self) -> None:
        """Test template with nested dict containing expressions."""
        template = ModelEnvelopeTemplate(
            operation="http_request",
            fields={
                "url": "${binding.config.api_url}",
                "headers": {
                    "Authorization": "Bearer ${request.token}",
                    "Content-Type": "application/json",
                },
            },
        )
        assert template.fields["headers"]["Content-Type"] == "application/json"

    def test_template_with_list_expressions(self) -> None:
        """Test template with list containing expressions."""
        template = ModelEnvelopeTemplate(
            operation="batch_process",
            fields={
                "items": ["${request.item1}", "${request.item2}"],
            },
        )
        assert len(template.fields["items"]) == 2

    def test_template_mixed_static_and_dynamic(self) -> None:
        """Test template with mixed static and dynamic values."""
        template = ModelEnvelopeTemplate(
            operation="write_file",
            fields={
                "path": "${binding.config.base_path}/snapshots/${request.id}.json",
                "encoding": "utf-8",
                "overwrite": True,
                "permissions": 644,
            },
        )
        assert template.fields["encoding"] == "utf-8"
        assert template.fields["overwrite"] is True
        assert template.fields["permissions"] == 644

    def test_empty_fields_allowed(self) -> None:
        """Test that empty fields dict is allowed."""
        template = ModelEnvelopeTemplate(operation="simple_op", fields={})
        assert template.fields == {}


@pytest.mark.unit
@pytest.mark.timeout(60)
class TestModelEnvelopeTemplateInvalid:
    """Tests for invalid ModelEnvelopeTemplate patterns."""

    def test_empty_operation_rejected(self) -> None:
        """Test that empty operation name is rejected."""
        with pytest.raises(ValidationError) as exc_info:
            ModelEnvelopeTemplate(operation="", fields={})
        assert "operation" in str(exc_info.value)

    def test_invalid_expression_root_rejected(self) -> None:
        """Test that invalid expression root in fields is rejected."""
        with pytest.raises(ValueError) as exc_info:
            ModelEnvelopeTemplate(
                operation="test",
                fields={"value": "${env.SECRET}"},
            )
        assert "must start with one of" in str(exc_info.value)

    def test_chained_pipes_in_fields_rejected(self) -> None:
        """Test that chained pipes in template fields are rejected."""
        with pytest.raises(ValueError) as exc_info:
            ModelEnvelopeTemplate(
                operation="test",
                fields={"value": "${request.data | to_json | from_json}"},
            )
        assert "Chained pipes not allowed" in str(exc_info.value)

    def test_double_underscore_in_fields_rejected(self) -> None:
        """Test that double underscore in field expressions is rejected."""
        with pytest.raises(ValueError) as exc_info:
            ModelEnvelopeTemplate(
                operation="test",
                fields={"value": "${request.__dict__}"},
            )
        assert "Security violation" in str(exc_info.value)

    def test_invalid_function_in_fields_rejected(self) -> None:
        """Test that invalid pipe function in fields is rejected."""
        with pytest.raises(ValueError) as exc_info:
            ModelEnvelopeTemplate(
                operation="test",
                fields={"value": "${request.data | invalid_func}"},
            )
        assert "must be one of" in str(exc_info.value)

    def test_nested_invalid_expression_rejected(self) -> None:
        """Test that invalid expression in nested structure is rejected."""
        with pytest.raises(ValueError) as exc_info:
            ModelEnvelopeTemplate(
                operation="test",
                fields={
                    "outer": {
                        "inner": "${env.SECRET}",
                    },
                },
            )
        assert "must start with one of" in str(exc_info.value)

    def test_empty_expression_whitespace_rejected(self) -> None:
        """Test that whitespace-only expression ${ } is rejected."""
        with pytest.raises(ValueError) as exc_info:
            ModelEnvelopeTemplate(
                operation="test",
                fields={"value": "${ }"},
            )
        assert "Empty expression" in str(exc_info.value)

    def test_literal_dollar_brace_not_validated(self) -> None:
        """Test that ${} without content is treated as literal (doesn't match pattern)."""
        # ${} doesn't match the expression pattern (requires at least 1 char)
        # so it passes through as a literal string without validation
        template = ModelEnvelopeTemplate(
            operation="test",
            fields={"value": "${}"},
        )
        assert template.fields["value"] == "${}"


# =============================================================================
# ModelResponseMapping Tests
# =============================================================================


@pytest.mark.unit
@pytest.mark.timeout(60)
class TestModelResponseMappingValid:
    """Tests for valid ModelResponseMapping patterns."""

    def test_basic_response_mapping(self) -> None:
        """Test basic response mapping creation."""
        mapping = ModelResponseMapping(
            fields={
                "status": "${result.status}",
                "data": "${result.payload}",
            }
        )
        assert "${result.status}" in mapping.fields["status"]

    def test_response_mapping_with_functions(self) -> None:
        """Test response mapping with pipe functions."""
        mapping = ModelResponseMapping(
            fields={
                "data": "${result.payload | from_json}",
                "serialized": "${request.body | to_json}",
            }
        )
        assert mapping.fields is not None

    def test_nested_response_mapping(self) -> None:
        """Test response mapping with nested structure."""
        mapping = ModelResponseMapping(
            fields={
                "data": {
                    "id": "${result.id}",
                    "name": "${result.name}",
                },
                "metadata": {
                    "request_id": "${request.request_id}",
                },
            }
        )
        assert mapping.fields["data"]["id"] == "${result.id}"

    def test_empty_fields_allowed(self) -> None:
        """Test that empty fields is allowed (response is optional)."""
        mapping = ModelResponseMapping(fields={})
        assert mapping.fields == {}

    def test_literal_values_allowed(self) -> None:
        """Test that literal values are allowed in mapping."""
        mapping = ModelResponseMapping(
            fields={
                "status": "${result.status}",
                "version": "1.0.0",
                "count": 42,
                "enabled": True,
            }
        )
        assert mapping.fields["version"] == "1.0.0"
        assert mapping.fields["count"] == 42


@pytest.mark.unit
@pytest.mark.timeout(60)
class TestModelResponseMappingInvalid:
    """Tests for invalid ModelResponseMapping patterns."""

    def test_invalid_expression_root_rejected(self) -> None:
        """Test that invalid expression root is rejected."""
        with pytest.raises(ValueError) as exc_info:
            ModelResponseMapping(fields={"value": "${env.VAR}"})
        assert "must start with one of" in str(exc_info.value)

    def test_ambiguous_config_root_rejected(self) -> None:
        """Test that ambiguous config root is rejected."""
        with pytest.raises(ValueError) as exc_info:
            ModelResponseMapping(fields={"value": "${config.setting}"})
        assert "binding.config" in str(exc_info.value) or "must start with" in str(
            exc_info.value
        )

    def test_ternary_operator_rejected(self) -> None:
        """Test that ternary operators are rejected."""
        with pytest.raises(ValueError) as exc_info:
            ModelResponseMapping(fields={"value": "${result.success ? 'yes' : 'no'}"})
        assert "Ternary operators not allowed" in str(exc_info.value)

    def test_bracket_notation_rejected(self) -> None:
        """Test that bracket notation is rejected."""
        with pytest.raises(ValueError) as exc_info:
            ModelResponseMapping(fields={"value": "${result.items[0]}"})
        assert "Bracket notation not allowed" in str(exc_info.value)

    def test_security_double_underscore_rejected(self) -> None:
        """Test that double underscore is rejected."""
        with pytest.raises(ValueError) as exc_info:
            ModelResponseMapping(fields={"value": "${result.__dict__}"})
        assert "Security violation" in str(exc_info.value)

    def test_security_denied_builtin_rejected(self) -> None:
        """Test that denied builtins are rejected."""
        with pytest.raises(ValueError) as exc_info:
            ModelResponseMapping(fields={"value": "${result.eval}"})
        assert "Security violation" in str(exc_info.value)
        assert "eval" in str(exc_info.value)

    def test_chained_pipes_rejected(self) -> None:
        """Test that chained pipes are rejected."""
        with pytest.raises(ValueError) as exc_info:
            ModelResponseMapping(
                fields={"value": "${result.data | to_json | from_json}"}
            )
        assert "Chained pipes not allowed" in str(exc_info.value)

    def test_max_depth_exceeded_rejected(self) -> None:
        """Test that excessive nesting depth is rejected."""
        # Build deeply nested structure (>20 levels)
        deep_dict: dict = {"value": "${result.data}"}
        for _ in range(25):
            deep_dict = {"nested": deep_dict}

        with pytest.raises(ValueError) as exc_info:
            ModelResponseMapping(fields=deep_dict)
        assert "maximum nesting depth" in str(exc_info.value)


@pytest.mark.unit
@pytest.mark.timeout(60)
class TestModelResponseMappingRepr:
    """Tests for ModelResponseMapping representation."""

    def test_repr_shows_field_count(self) -> None:
        """Test __repr__ shows field count."""
        mapping = ModelResponseMapping(fields={"a": "${result.a}", "b": "${result.b}"})
        repr_str = repr(mapping)
        assert "ModelResponseMapping" in repr_str
        assert "2 fields" in repr_str


# =============================================================================
# ModelOperationMapping Tests
# =============================================================================


@pytest.mark.unit
@pytest.mark.timeout(60)
class TestModelOperationMappingValid:
    """Tests for valid ModelOperationMapping patterns."""

    def test_mapping_with_envelope_only(self) -> None:
        """Test operation mapping with envelope only (no response)."""
        mapping = ModelOperationMapping(
            envelope=ModelEnvelopeTemplate(
                operation="write_file",
                fields={"path": "/output.json"},
            ),
            response=None,
        )
        assert mapping.envelope.operation == "write_file"
        assert mapping.response is None

    def test_mapping_with_envelope_and_response(self) -> None:
        """Test operation mapping with both envelope and response."""
        mapping = ModelOperationMapping(
            envelope=ModelEnvelopeTemplate(
                operation="read_file",
                fields={"path": "${binding.config.base_path}/input.json"},
            ),
            response=ModelResponseMapping(
                fields={
                    "content": "${result.data}",
                    "status": "${result.status}",
                }
            ),
        )
        assert mapping.envelope.operation == "read_file"
        assert mapping.response is not None
        assert "content" in mapping.response.fields

    def test_mapping_with_description(self) -> None:
        """Test operation mapping with description."""
        mapping = ModelOperationMapping(
            envelope=ModelEnvelopeTemplate(operation="test_op", fields={}),
            description="Performs a test operation",
        )
        assert mapping.description == "Performs a test operation"

    def test_repr_format(self) -> None:
        """Test __repr__ output format."""
        mapping = ModelOperationMapping(
            envelope=ModelEnvelopeTemplate(operation="my_op", fields={}),
            response=ModelResponseMapping(fields={"x": "${result.x}"}),
        )
        repr_str = repr(mapping)
        assert "ModelOperationMapping" in repr_str
        assert "my_op" in repr_str
        assert "has_response=True" in repr_str


@pytest.mark.unit
@pytest.mark.timeout(60)
class TestModelOperationMappingInvalid:
    """Tests for invalid ModelOperationMapping patterns."""

    def test_missing_envelope_rejected(self) -> None:
        """Test that missing envelope is rejected."""
        with pytest.raises(ValidationError):
            ModelOperationMapping()  # type: ignore[call-arg]

    def test_invalid_envelope_expression_rejected(self) -> None:
        """Test that invalid expression in envelope is rejected."""
        with pytest.raises(ValueError):
            ModelOperationMapping(
                envelope=ModelEnvelopeTemplate(
                    operation="test",
                    fields={"value": "${env.SECRET}"},
                )
            )


# =============================================================================
# ModelOperationBindings Tests
# =============================================================================


@pytest.mark.unit
@pytest.mark.timeout(60)
class TestModelOperationBindingsValid:
    """Tests for valid ModelOperationBindings patterns."""

    def test_minimal_valid_binding(self) -> None:
        """Test minimal valid operation binding."""
        binding = ModelOperationBindings(
            version=DEFAULT_VERSION,
            handler="mymodule.handlers.MyHandler",
            mappings={
                "process": ModelOperationMapping(
                    envelope=ModelEnvelopeTemplate(operation="do_work", fields={})
                )
            },
        )
        assert binding.handler == "mymodule.handlers.MyHandler"
        assert "process" in binding.mappings

    def test_full_binding_with_config(self) -> None:
        """Test full binding with config and multiple mappings."""
        binding = ModelOperationBindings(
            version=DEFAULT_VERSION,
            handler="omnibase_infra.handlers.handler_filesystem.HandlerFileSystem",
            config={
                "base_path": "${contract.config.base_path}",
                "allowed_paths": ["${contract.config.base_path}"],
            },
            mappings={
                "store": ModelOperationMapping(
                    envelope=ModelEnvelopeTemplate(
                        operation="write_file",
                        fields={
                            "path": "${binding.config.base_path}/output.json",
                            "content": "${request.data | to_json}",
                        },
                    ),
                    response=ModelResponseMapping(
                        fields={
                            "status": "${result.status}",
                            "bytes_written": "${result.bytes_written}",
                        }
                    ),
                ),
                "retrieve": ModelOperationMapping(
                    envelope=ModelEnvelopeTemplate(
                        operation="read_file",
                        fields={"path": "${binding.config.base_path}/input.json"},
                    ),
                    response=ModelResponseMapping(
                        fields={"content": "${result.data | from_json}"}
                    ),
                ),
            },
            description="Filesystem storage binding",
        )
        assert len(binding.mappings) == 2
        assert binding.config is not None
        assert binding.description == "Filesystem storage binding"

    def test_handler_path_with_multiple_segments(self) -> None:
        """Test handler path with multiple package segments."""
        binding = ModelOperationBindings(
            version=DEFAULT_VERSION,
            handler="package.subpackage.module.ClassName",
            mappings={
                "op": ModelOperationMapping(
                    envelope=ModelEnvelopeTemplate(operation="test", fields={})
                )
            },
        )
        assert binding.handler == "package.subpackage.module.ClassName"


@pytest.mark.unit
@pytest.mark.timeout(60)
class TestModelOperationBindingsHandlerValidation:
    """Tests for handler path validation in ModelOperationBindings."""

    def test_handler_no_dot_rejected(self) -> None:
        """Test that handler without dot is rejected."""
        with pytest.raises(ModelOnexError) as exc_info:
            ModelOperationBindings(
                version=DEFAULT_VERSION,
                handler="SingleName",
                mappings={
                    "op": ModelOperationMapping(
                        envelope=ModelEnvelopeTemplate(operation="test", fields={})
                    )
                },
            )
        assert "dotted import path" in str(exc_info.value)
        assert "at least one dot" in str(exc_info.value)

    def test_handler_double_underscore_rejected(self) -> None:
        """Test that handler with double underscore is rejected (security)."""
        with pytest.raises(ModelOnexError) as exc_info:
            ModelOperationBindings(
                version=DEFAULT_VERSION,
                handler="module.__import__.Handler",
                mappings={
                    "op": ModelOperationMapping(
                        envelope=ModelEnvelopeTemplate(operation="test", fields={})
                    )
                },
            )
        assert "double underscore" in str(exc_info.value).lower()

    def test_handler_empty_rejected(self) -> None:
        """Test that empty handler is rejected."""
        with pytest.raises(ModelOnexError) as exc_info:
            ModelOperationBindings(
                version=DEFAULT_VERSION,
                handler="",
                mappings={
                    "op": ModelOperationMapping(
                        envelope=ModelEnvelopeTemplate(operation="test", fields={})
                    )
                },
            )
        assert "cannot be empty" in str(exc_info.value)

    def test_handler_non_string_rejected(self) -> None:
        """Test that non-string handler is rejected."""
        with pytest.raises(ModelOnexError) as exc_info:
            ModelOperationBindings(
                version=DEFAULT_VERSION,
                handler=123,  # type: ignore[arg-type]
                mappings={
                    "op": ModelOperationMapping(
                        envelope=ModelEnvelopeTemplate(operation="test", fields={})
                    )
                },
            )
        assert "must be a string" in str(exc_info.value)

    def test_handler_invalid_identifier_rejected(self) -> None:
        """Test that handler with invalid identifier is rejected."""
        with pytest.raises(ModelOnexError) as exc_info:
            ModelOperationBindings(
                version=DEFAULT_VERSION,
                handler="module.123invalid",  # starts with number
                mappings={
                    "op": ModelOperationMapping(
                        envelope=ModelEnvelopeTemplate(operation="test", fields={})
                    )
                },
            )
        assert "Invalid handler path format" in str(exc_info.value)


@pytest.mark.unit
@pytest.mark.timeout(60)
class TestModelOperationBindingsConfigValidation:
    """Tests for config expression validation in ModelOperationBindings."""

    def test_config_with_binding_config_root(self) -> None:
        """Test that binding.config root is allowed in config."""
        binding = ModelOperationBindings(
            version=DEFAULT_VERSION,
            handler="module.Handler",
            config={"path": "${binding.config.path}"},
            mappings={
                "op": ModelOperationMapping(
                    envelope=ModelEnvelopeTemplate(operation="test", fields={})
                )
            },
        )
        assert binding.config is not None

    def test_config_with_contract_config_root(self) -> None:
        """Test that contract.config root is allowed in config."""
        binding = ModelOperationBindings(
            version=DEFAULT_VERSION,
            handler="module.Handler",
            config={"path": "${contract.config.base_path}"},
            mappings={
                "op": ModelOperationMapping(
                    envelope=ModelEnvelopeTemplate(operation="test", fields={})
                )
            },
        )
        assert binding.config is not None

    def test_config_request_root_rejected(self) -> None:
        """Test that request root is rejected in config (only at runtime)."""
        with pytest.raises(ModelOnexError) as exc_info:
            ModelOperationBindings(
                version=DEFAULT_VERSION,
                handler="module.Handler",
                config={"value": "${request.field}"},
                mappings={
                    "op": ModelOperationMapping(
                        envelope=ModelEnvelopeTemplate(operation="test", fields={})
                    )
                },
            )
        assert "binding.config" in str(exc_info.value) or "contract.config" in str(
            exc_info.value
        )

    def test_config_result_root_rejected(self) -> None:
        """Test that result root is rejected in config."""
        with pytest.raises(ModelOnexError) as exc_info:
            ModelOperationBindings(
                version=DEFAULT_VERSION,
                handler="module.Handler",
                config={"value": "${result.data}"},
                mappings={
                    "op": ModelOperationMapping(
                        envelope=ModelEnvelopeTemplate(operation="test", fields={})
                    )
                },
            )
        assert "binding.config" in str(exc_info.value) or "contract.config" in str(
            exc_info.value
        )

    def test_config_double_underscore_rejected(self) -> None:
        """Test that double underscore in config expression is rejected."""
        with pytest.raises(ModelOnexError) as exc_info:
            ModelOperationBindings(
                version=DEFAULT_VERSION,
                handler="module.Handler",
                config={"value": "${binding.config.__dict__}"},
                mappings={
                    "op": ModelOperationMapping(
                        envelope=ModelEnvelopeTemplate(operation="test", fields={})
                    )
                },
            )
        assert "double underscore" in str(exc_info.value).lower()

    def test_config_denied_builtin_rejected(self) -> None:
        """Test that denied builtin in config expression is rejected."""
        with pytest.raises(ModelOnexError) as exc_info:
            ModelOperationBindings(
                version=DEFAULT_VERSION,
                handler="module.Handler",
                config={"value": "${binding.config.eval}"},
                mappings={
                    "op": ModelOperationMapping(
                        envelope=ModelEnvelopeTemplate(operation="test", fields={})
                    )
                },
            )
        assert "Security violation" in str(exc_info.value)
        assert "eval" in str(exc_info.value)

    def test_config_nested_expressions_validated(self) -> None:
        """Test that nested config expressions are validated."""
        with pytest.raises(ModelOnexError) as exc_info:
            ModelOperationBindings(
                version=DEFAULT_VERSION,
                handler="module.Handler",
                config={
                    "outer": {
                        "inner": "${env.SECRET}",  # Invalid root
                    }
                },
                mappings={
                    "op": ModelOperationMapping(
                        envelope=ModelEnvelopeTemplate(operation="test", fields={})
                    )
                },
            )
        assert "binding.config" in str(exc_info.value) or "contract.config" in str(
            exc_info.value
        )

    def test_config_list_expressions_validated(self) -> None:
        """Test that list expressions in config are validated."""
        with pytest.raises(ModelOnexError) as exc_info:
            ModelOperationBindings(
                version=DEFAULT_VERSION,
                handler="module.Handler",
                config={
                    "paths": ["${env.PATH1}", "${env.PATH2}"],  # Invalid roots
                },
                mappings={
                    "op": ModelOperationMapping(
                        envelope=ModelEnvelopeTemplate(operation="test", fields={})
                    )
                },
            )
        assert "binding.config" in str(exc_info.value) or "contract.config" in str(
            exc_info.value
        )


@pytest.mark.unit
@pytest.mark.timeout(60)
class TestModelOperationBindingsMappingsValidation:
    """Tests for mappings validation in ModelOperationBindings."""

    def test_empty_mappings_rejected(self) -> None:
        """Test that empty mappings dict is rejected."""
        with pytest.raises(ModelOnexError) as exc_info:
            ModelOperationBindings(
                version=DEFAULT_VERSION,
                handler="module.Handler",
                mappings={},
            )
        assert "at least one mapping" in str(exc_info.value)


@pytest.mark.unit
@pytest.mark.timeout(60)
class TestModelOperationBindingsHelperMethods:
    """Tests for ModelOperationBindings helper methods."""

    def test_get_all_operation_names(self) -> None:
        """Test get_all_operation_names returns all operation keys."""
        binding = ModelOperationBindings(
            version=DEFAULT_VERSION,
            handler="module.Handler",
            mappings={
                "store": ModelOperationMapping(
                    envelope=ModelEnvelopeTemplate(operation="write", fields={})
                ),
                "retrieve": ModelOperationMapping(
                    envelope=ModelEnvelopeTemplate(operation="read", fields={})
                ),
                "delete": ModelOperationMapping(
                    envelope=ModelEnvelopeTemplate(operation="remove", fields={})
                ),
            },
        )
        names = binding.get_all_operation_names()
        assert names == {"store", "retrieve", "delete"}

    def test_get_mapping_existing(self) -> None:
        """Test get_mapping returns mapping for existing operation."""
        store_mapping = ModelOperationMapping(
            envelope=ModelEnvelopeTemplate(operation="write", fields={})
        )
        binding = ModelOperationBindings(
            version=DEFAULT_VERSION,
            handler="module.Handler",
            mappings={"store": store_mapping},
        )
        result = binding.get_mapping("store")
        assert result is store_mapping

    def test_get_mapping_non_existing(self) -> None:
        """Test get_mapping returns None for non-existing operation."""
        binding = ModelOperationBindings(
            version=DEFAULT_VERSION,
            handler="module.Handler",
            mappings={
                "store": ModelOperationMapping(
                    envelope=ModelEnvelopeTemplate(operation="write", fields={})
                )
            },
        )
        result = binding.get_mapping("nonexistent")
        assert result is None


@pytest.mark.unit
@pytest.mark.timeout(60)
class TestModelOperationBindingsRepr:
    """Tests for ModelOperationBindings representation."""

    def test_repr_format(self) -> None:
        """Test __repr__ output format."""
        binding = ModelOperationBindings(
            version=DEFAULT_VERSION,
            handler="package.module.Handler",
            mappings={
                "op1": ModelOperationMapping(
                    envelope=ModelEnvelopeTemplate(operation="test1", fields={})
                ),
                "op2": ModelOperationMapping(
                    envelope=ModelEnvelopeTemplate(operation="test2", fields={})
                ),
            },
        )
        repr_str = repr(binding)
        assert "ModelOperationBindings" in repr_str
        assert "package.module.Handler" in repr_str
        assert "op1" in repr_str or "op2" in repr_str


@pytest.mark.unit
@pytest.mark.timeout(60)
class TestModelOperationBindingsSerialization:
    """Tests for ModelOperationBindings serialization."""

    def test_model_dump_round_trip(self) -> None:
        """Test model can be serialized and deserialized."""
        original = ModelOperationBindings(
            version=DEFAULT_VERSION,
            handler="module.Handler",
            config={"path": "${contract.config.path}"},
            mappings={
                "store": ModelOperationMapping(
                    envelope=ModelEnvelopeTemplate(
                        operation="write",
                        fields={"path": "${binding.config.path}"},
                    ),
                    response=ModelResponseMapping(
                        fields={"status": "${result.status}"}
                    ),
                )
            },
            description="Test binding",
        )

        # Serialize
        data = original.model_dump()

        # Deserialize
        restored = ModelOperationBindings.model_validate(data)

        assert restored.handler == original.handler
        assert restored.description == original.description
        assert "store" in restored.mappings

    def test_extra_fields_ignored(self) -> None:
        """Test that extra fields are ignored per model config."""
        data = {
            "version": {"major": 1, "minor": 0, "patch": 0},
            "handler": "module.Handler",
            "mappings": {
                "op": {
                    "envelope": {"operation": "test", "fields": {}},
                }
            },
            "unknown_field": "should be ignored",
        }
        binding = ModelOperationBindings.model_validate(data)
        assert not hasattr(binding, "unknown_field")


# =============================================================================
# Integration Tests
# =============================================================================


@pytest.mark.unit
@pytest.mark.timeout(60)
class TestOperationBindingsIntegration:
    """Integration tests for the full operation bindings DSL."""

    def test_full_filesystem_binding_example(self) -> None:
        """Test realistic filesystem binding configuration."""
        binding = ModelOperationBindings(
            version=ModelSemVer(major=1, minor=0, patch=0),
            handler="omnibase_infra.handlers.handler_filesystem.HandlerFileSystem",
            config={
                "base_path": "${contract.config.base_path}",
                "allowed_paths": ["${contract.config.base_path}"],
            },
            mappings={
                "store": ModelOperationMapping(
                    envelope=ModelEnvelopeTemplate(
                        operation="write_file",
                        fields={
                            "path": "${binding.config.base_path}/snapshots/${request.snapshot.snapshot_id}.json",
                            "content": "${request.snapshot | to_json}",
                            "mode": "w",
                            "encoding": "utf-8",
                        },
                    ),
                    response=ModelResponseMapping(
                        fields={
                            "status": "${result.status}",
                            "snapshot": "${request.snapshot}",
                            "error_message": "${result.error_message}",
                            "bytes_written": "${result.bytes_written}",
                        }
                    ),
                    description="Persist snapshot to filesystem",
                ),
                "retrieve": ModelOperationMapping(
                    envelope=ModelEnvelopeTemplate(
                        operation="read_file",
                        fields={
                            "path": "${binding.config.base_path}/snapshots/${request.snapshot_id}.json",
                            "encoding": "utf-8",
                        },
                    ),
                    response=ModelResponseMapping(
                        fields={
                            "snapshot": "${result.content | from_json}",
                            "status": "${result.status}",
                            "error_message": "${result.error_message}",
                        }
                    ),
                    description="Retrieve snapshot from filesystem",
                ),
            },
            description="Filesystem-backed snapshot storage",
        )

        # Verify structure
        assert binding.get_all_operation_names() == {"store", "retrieve"}
        store_mapping = binding.get_mapping("store")
        assert store_mapping is not None
        assert store_mapping.envelope.operation == "write_file"
        assert store_mapping.response is not None
        assert "status" in store_mapping.response.fields

    def test_binding_expression_property_consistency(self) -> None:
        """Test that expression properties are consistent across the DSL."""
        # Create binding expression
        expr = ModelBindingExpression(raw="${binding.config.base_path}")

        # Verify properties match what envelope template would use
        assert expr.root == "binding.config"
        assert expr.path == "base_path"
        assert expr.full_path == "binding.config.base_path"

        # Create envelope template with same expression
        template = ModelEnvelopeTemplate(
            operation="test",
            fields={"path": "${binding.config.base_path}/output.json"},
        )
        assert template.fields["path"] == "${binding.config.base_path}/output.json"
