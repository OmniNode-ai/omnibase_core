"""Unit tests for Contract-Driven NodeCompute v1.0 transformations and executor."""

from uuid import uuid4

import pytest

from omnibase_core.enums.enum_case_mode import EnumCaseMode
from omnibase_core.enums.enum_compute_step_type import EnumComputeStepType
from omnibase_core.enums.enum_regex_flag import EnumRegexFlag
from omnibase_core.enums.enum_transformation_type import EnumTransformationType
from omnibase_core.enums.enum_trim_mode import EnumTrimMode
from omnibase_core.enums.enum_unicode_form import EnumUnicodeForm
from omnibase_core.models.compute.model_compute_execution_context import (
    ModelComputeExecutionContext,
)
from omnibase_core.models.compute.model_compute_step_metadata import (
    ModelComputeStepMetadata,
)
from omnibase_core.models.compute.model_compute_step_result import (
    ModelComputeStepResult,
)
from omnibase_core.models.contracts.subcontracts.model_compute_pipeline_step import (
    ModelComputePipelineStep,
)
from omnibase_core.models.contracts.subcontracts.model_compute_subcontract import (
    ModelComputeSubcontract,
)
from omnibase_core.models.errors.model_onex_error import ModelOnexError
from omnibase_core.models.transformations.model_transform_case_config import (
    ModelTransformCaseConfig,
)
from omnibase_core.models.transformations.model_transform_json_path_config import (
    ModelTransformJsonPathConfig,
)
from omnibase_core.models.transformations.model_transform_regex_config import (
    ModelTransformRegexConfig,
)
from omnibase_core.models.transformations.model_transform_trim_config import (
    ModelTransformTrimConfig,
)
from omnibase_core.models.transformations.model_transform_unicode_config import (
    ModelTransformUnicodeConfig,
)
from omnibase_core.utils.util_compute_executor import (
    execute_compute_pipeline,
    resolve_mapping_path,
)
from omnibase_core.utils.util_compute_transformations import (
    execute_transformation,
    transform_case,
    transform_identity,
    transform_json_path,
    transform_regex,
    transform_trim,
    transform_unicode,
)


@pytest.mark.timeout(5)
@pytest.mark.unit
class TestTransformIdentity:
    """Tests for identity transformation."""

    def test_returns_same_value(self) -> None:
        """Test identity returns input unchanged."""
        assert transform_identity("hello", None) == "hello"
        assert transform_identity(123, None) == 123
        assert transform_identity({"key": "value"}, None) == {"key": "value"}
        assert transform_identity(None, None) is None

    def test_with_list(self) -> None:
        """Test identity with list input."""
        data = [1, 2, 3]
        assert transform_identity(data, None) == [1, 2, 3]

    def test_with_nested_structure(self) -> None:
        """Test identity with nested data structure."""
        data = {"outer": {"inner": [1, 2, {"deep": True}]}}
        assert transform_identity(data, None) == data


@pytest.mark.timeout(5)
@pytest.mark.unit
class TestTransformRegex:
    """Tests for regex transformation."""

    def test_simple_replacement(self) -> None:
        """Test simple regex replacement."""
        config = ModelTransformRegexConfig(pattern=r"\s+", replacement=" ")
        result = transform_regex("hello   world", config)
        assert result == "hello world"

    def test_with_ignorecase(self) -> None:
        """Test regex with IGNORECASE flag."""
        config = ModelTransformRegexConfig(
            pattern=r"hello",
            replacement="hi",
            flags=[EnumRegexFlag.IGNORECASE],
        )
        result = transform_regex("HELLO world", config)
        assert result == "hi world"

    def test_with_multiline(self) -> None:
        """Test regex with MULTILINE flag."""
        config = ModelTransformRegexConfig(
            pattern=r"^line",
            replacement="row",
            flags=[EnumRegexFlag.MULTILINE],
        )
        result = transform_regex("line1\nline2", config)
        assert result == "row1\nrow2"

    def test_with_dotall(self) -> None:
        """Test regex with DOTALL flag."""
        config = ModelTransformRegexConfig(
            pattern=r"a.b",
            replacement="X",
            flags=[EnumRegexFlag.DOTALL],
        )
        result = transform_regex("a\nb", config)
        assert result == "X"

    def test_invalid_input_type(self) -> None:
        """Test regex rejects non-string input."""
        config = ModelTransformRegexConfig(pattern=r"\d+")
        with pytest.raises(ModelOnexError):
            transform_regex(123, config)

    def test_invalid_regex_pattern(self) -> None:
        """Test regex raises error on invalid pattern."""
        config = ModelTransformRegexConfig(pattern=r"[invalid", replacement="x")
        with pytest.raises(ModelOnexError):
            transform_regex("test", config)


@pytest.mark.timeout(5)
@pytest.mark.unit
class TestTransformCase:
    """Tests for case transformation."""

    def test_uppercase(self) -> None:
        """Test uppercase transformation."""
        config = ModelTransformCaseConfig(mode=EnumCaseMode.UPPER)
        assert transform_case("hello world", config) == "HELLO WORLD"

    def test_lowercase(self) -> None:
        """Test lowercase transformation."""
        config = ModelTransformCaseConfig(mode=EnumCaseMode.LOWER)
        assert transform_case("HELLO WORLD", config) == "hello world"

    def test_titlecase(self) -> None:
        """Test titlecase transformation."""
        config = ModelTransformCaseConfig(mode=EnumCaseMode.TITLE)
        assert transform_case("hello world", config) == "Hello World"

    def test_invalid_input_type(self) -> None:
        """Test case rejects non-string input."""
        config = ModelTransformCaseConfig(mode=EnumCaseMode.UPPER)
        with pytest.raises(ModelOnexError):
            transform_case(123, config)

    def test_empty_string(self) -> None:
        """Test case transformation with empty string."""
        config = ModelTransformCaseConfig(mode=EnumCaseMode.UPPER)
        assert transform_case("", config) == ""


@pytest.mark.timeout(5)
@pytest.mark.unit
class TestTransformTrim:
    """Tests for trim transformation."""

    def test_trim_both(self) -> None:
        """Test trimming both sides."""
        config = ModelTransformTrimConfig(mode=EnumTrimMode.BOTH)
        assert transform_trim("  hello  ", config) == "hello"

    def test_trim_left(self) -> None:
        """Test trimming left side only."""
        config = ModelTransformTrimConfig(mode=EnumTrimMode.LEFT)
        assert transform_trim("  hello  ", config) == "hello  "

    def test_trim_right(self) -> None:
        """Test trimming right side only."""
        config = ModelTransformTrimConfig(mode=EnumTrimMode.RIGHT)
        assert transform_trim("  hello  ", config) == "  hello"

    def test_trim_invalid_input_type(self) -> None:
        """Test trim rejects non-string input."""
        config = ModelTransformTrimConfig(mode=EnumTrimMode.BOTH)
        with pytest.raises(ModelOnexError):
            transform_trim(123, config)

    def test_trim_no_whitespace(self) -> None:
        """Test trim with no leading/trailing whitespace."""
        config = ModelTransformTrimConfig(mode=EnumTrimMode.BOTH)
        assert transform_trim("hello", config) == "hello"


@pytest.mark.timeout(5)
@pytest.mark.unit
class TestTransformUnicode:
    """Tests for unicode normalization."""

    def test_nfc_normalization(self) -> None:
        """Test NFC normalization."""
        config = ModelTransformUnicodeConfig(form=EnumUnicodeForm.NFC)
        # e can be composed (NFC) or decomposed (NFD)
        decomposed = "e\u0301"  # e + combining acute accent
        result = transform_unicode(decomposed, config)
        assert result == "\xe9"  # composed form (e-acute)

    def test_nfd_normalization(self) -> None:
        """Test NFD normalization."""
        config = ModelTransformUnicodeConfig(form=EnumUnicodeForm.NFD)
        composed = "\xe9"  # composed form (e-acute)
        result = transform_unicode(composed, config)
        assert len(result) == 2  # decomposed into e + combining accent

    def test_unicode_invalid_input_type(self) -> None:
        """Test unicode rejects non-string input."""
        config = ModelTransformUnicodeConfig(form=EnumUnicodeForm.NFC)
        with pytest.raises(ModelOnexError):
            transform_unicode(123, config)


@pytest.mark.timeout(5)
@pytest.mark.unit
class TestTransformJsonPath:
    """Tests for JSONPath extraction."""

    def test_simple_field(self) -> None:
        """Test extracting simple field."""
        config = ModelTransformJsonPathConfig(path="$.name")
        data = {"name": "John", "age": 30}
        assert transform_json_path(data, config) == "John"

    def test_nested_field(self) -> None:
        """Test extracting nested field."""
        config = ModelTransformJsonPathConfig(path="$.user.name")
        data = {"user": {"name": "Jane", "id": 123}}
        assert transform_json_path(data, config) == "Jane"

    def test_missing_field(self) -> None:
        """Test error on missing field."""
        config = ModelTransformJsonPathConfig(path="$.missing")
        data = {"name": "John"}
        with pytest.raises(ModelOnexError):
            transform_json_path(data, config)

    def test_root_access(self) -> None:
        """Test accessing root with $."""
        config = ModelTransformJsonPathConfig(path="$")
        data = {"name": "John"}
        assert transform_json_path(data, config) == data

    def test_deeply_nested_field(self) -> None:
        """Test extracting deeply nested field."""
        config = ModelTransformJsonPathConfig(path="$.a.b.c.d")
        data = {"a": {"b": {"c": {"d": "deep"}}}}
        assert transform_json_path(data, config) == "deep"


@pytest.mark.timeout(5)
@pytest.mark.unit
class TestExecuteTransformation:
    """Tests for execute_transformation dispatcher."""

    def test_identity_no_config(self) -> None:
        """Test identity works without config."""
        result = execute_transformation("hello", EnumTransformationType.IDENTITY, None)
        assert result == "hello"

    def test_case_with_config(self) -> None:
        """Test case conversion with config."""
        config = ModelTransformCaseConfig(mode=EnumCaseMode.UPPER)
        result = execute_transformation(
            "hello", EnumTransformationType.CASE_CONVERSION, config
        )
        assert result == "HELLO"

    def test_requires_config_for_non_identity(self) -> None:
        """Test non-identity transformations require config."""
        with pytest.raises(ModelOnexError):
            execute_transformation("hello", EnumTransformationType.REGEX, None)

    def test_trim_with_config(self) -> None:
        """Test trim transformation via dispatcher."""
        config = ModelTransformTrimConfig(mode=EnumTrimMode.BOTH)
        result = execute_transformation(
            "  hello  ", EnumTransformationType.TRIM, config
        )
        assert result == "hello"

    def test_unicode_with_config(self) -> None:
        """Test unicode normalization via dispatcher."""
        config = ModelTransformUnicodeConfig(form=EnumUnicodeForm.NFC)
        decomposed = "e\u0301"
        result = execute_transformation(
            decomposed, EnumTransformationType.NORMALIZE_UNICODE, config
        )
        assert result == "\xe9"


@pytest.mark.timeout(5)
@pytest.mark.unit
class TestResolveMappingPath:
    """Tests for resolve_mapping_path."""

    def test_full_input(self) -> None:
        """Test resolving $.input."""
        input_data = {"text": "hello"}
        result = resolve_mapping_path("$.input", input_data, {})
        assert result == input_data

    def test_input_field(self) -> None:
        """Test resolving $.input.<field>."""
        input_data = {"text": "hello", "count": 5}
        result = resolve_mapping_path("$.input.text", input_data, {})
        assert result == "hello"

    def test_nested_input_field(self) -> None:
        """Test resolving $.input.<field>.<subfield>."""
        input_data = {"user": {"name": "John", "id": 123}}
        result = resolve_mapping_path("$.input.user.name", input_data, {})
        assert result == "John"

    def test_step_output(self) -> None:
        """Test resolving $.steps.<name>.output."""
        metadata = ModelComputeStepMetadata(duration_ms=5.0)
        step_result = ModelComputeStepResult(
            step_name="transform",
            output="HELLO",
            metadata=metadata,
        )
        step_results = {"transform": step_result}

        result = resolve_mapping_path("$.steps.transform.output", {}, step_results)
        assert result == "HELLO"

    def test_step_without_output_suffix(self) -> None:
        """Test resolving $.steps.<name> returns output."""
        metadata = ModelComputeStepMetadata(duration_ms=5.0)
        step_result = ModelComputeStepResult(
            step_name="transform",
            output="HELLO",
            metadata=metadata,
        )
        step_results = {"transform": step_result}

        result = resolve_mapping_path("$.steps.transform", {}, step_results)
        assert result == "HELLO"

    def test_invalid_path_prefix(self) -> None:
        """Test error on invalid path prefix."""
        with pytest.raises(ModelOnexError):
            resolve_mapping_path("invalid.path", {}, {})

    def test_missing_input_field(self) -> None:
        """Test error on missing input field."""
        input_data = {"name": "John"}
        with pytest.raises(ModelOnexError):
            resolve_mapping_path("$.input.missing", input_data, {})

    def test_missing_step(self) -> None:
        """Test error on missing step."""
        with pytest.raises(ModelOnexError):
            resolve_mapping_path("$.steps.nonexistent.output", {}, {})

    def test_invalid_step_subpath(self) -> None:
        """Test error on invalid step subpath."""
        metadata = ModelComputeStepMetadata(duration_ms=5.0)
        step_result = ModelComputeStepResult(
            step_name="transform",
            output="HELLO",
            metadata=metadata,
        )
        step_results = {"transform": step_result}

        with pytest.raises(ModelOnexError):
            resolve_mapping_path("$.steps.transform.invalid", {}, step_results)


@pytest.mark.timeout(30)
@pytest.mark.unit
class TestExecuteComputePipeline:
    """Tests for execute_compute_pipeline.

    Note: 30-second timeout protects against pipeline execution hangs.
    """

    def test_simple_pipeline(self) -> None:
        """Test executing a simple transformation pipeline."""
        contract = ModelComputeSubcontract(
            operation_name="text_upper",
            operation_version={"major": 1, "minor": 0, "patch": 0},
            pipeline=[
                ModelComputePipelineStep(
                    step_name="to_upper",
                    step_type=EnumComputeStepType.TRANSFORMATION,
                    transformation_type=EnumTransformationType.CASE_CONVERSION,
                    transformation_config=ModelTransformCaseConfig(
                        mode=EnumCaseMode.UPPER
                    ),
                ),
            ],
        )
        context = ModelComputeExecutionContext(operation_id=uuid4())

        result = execute_compute_pipeline(contract, "hello world", context)

        assert result.success is True
        assert result.output == "HELLO WORLD"
        assert result.steps_executed == ["to_upper"]
        assert "to_upper" in result.step_results

    def test_multi_step_pipeline(self) -> None:
        """Test executing a multi-step pipeline."""
        contract = ModelComputeSubcontract(
            operation_name="text_normalize",
            operation_version={"major": 1, "minor": 0, "patch": 0},
            pipeline=[
                ModelComputePipelineStep(
                    step_name="trim",
                    step_type=EnumComputeStepType.TRANSFORMATION,
                    transformation_type=EnumTransformationType.TRIM,
                    transformation_config=ModelTransformTrimConfig(
                        mode=EnumTrimMode.BOTH
                    ),
                ),
                ModelComputePipelineStep(
                    step_name="to_upper",
                    step_type=EnumComputeStepType.TRANSFORMATION,
                    transformation_type=EnumTransformationType.CASE_CONVERSION,
                    transformation_config=ModelTransformCaseConfig(
                        mode=EnumCaseMode.UPPER
                    ),
                ),
            ],
        )
        context = ModelComputeExecutionContext(operation_id=uuid4())

        result = execute_compute_pipeline(contract, "  hello world  ", context)

        assert result.success is True
        assert result.output == "HELLO WORLD"
        assert result.steps_executed == ["trim", "to_upper"]

    def test_abort_on_failure(self) -> None:
        """Test pipeline aborts on first failure."""
        contract = ModelComputeSubcontract(
            operation_name="failing_pipeline",
            operation_version={"major": 1, "minor": 0, "patch": 0},
            pipeline=[
                ModelComputePipelineStep(
                    step_name="to_upper",
                    step_type=EnumComputeStepType.TRANSFORMATION,
                    transformation_type=EnumTransformationType.CASE_CONVERSION,
                    transformation_config=ModelTransformCaseConfig(
                        mode=EnumCaseMode.UPPER
                    ),
                ),
                ModelComputePipelineStep(
                    step_name="never_reached",
                    step_type=EnumComputeStepType.TRANSFORMATION,
                    transformation_type=EnumTransformationType.IDENTITY,
                ),
            ],
        )
        context = ModelComputeExecutionContext(operation_id=uuid4())

        # Pass integer to cause failure in case conversion
        result = execute_compute_pipeline(contract, 123, context)

        assert result.success is False
        assert result.error_step == "to_upper"
        assert "never_reached" not in result.step_results

    def test_identity_transformation(self) -> None:
        """Test identity transformation in pipeline."""
        contract = ModelComputeSubcontract(
            operation_name="passthrough",
            operation_version={"major": 1, "minor": 0, "patch": 0},
            pipeline=[
                ModelComputePipelineStep(
                    step_name="identity",
                    step_type=EnumComputeStepType.TRANSFORMATION,
                    transformation_type=EnumTransformationType.IDENTITY,
                    # No transformation_config for IDENTITY
                ),
            ],
        )
        context = ModelComputeExecutionContext(operation_id=uuid4())

        result = execute_compute_pipeline(contract, {"data": "unchanged"}, context)

        assert result.success is True
        assert result.output == {"data": "unchanged"}

    def test_disabled_step_skipped(self) -> None:
        """Test disabled steps are skipped."""
        contract = ModelComputeSubcontract(
            operation_name="with_disabled",
            operation_version={"major": 1, "minor": 0, "patch": 0},
            pipeline=[
                ModelComputePipelineStep(
                    step_name="disabled_step",
                    step_type=EnumComputeStepType.TRANSFORMATION,
                    transformation_type=EnumTransformationType.CASE_CONVERSION,
                    transformation_config=ModelTransformCaseConfig(
                        mode=EnumCaseMode.UPPER
                    ),
                    enabled=False,
                ),
                ModelComputePipelineStep(
                    step_name="enabled_step",
                    step_type=EnumComputeStepType.TRANSFORMATION,
                    transformation_type=EnumTransformationType.TRIM,
                    transformation_config=ModelTransformTrimConfig(
                        mode=EnumTrimMode.BOTH
                    ),
                ),
            ],
        )
        context = ModelComputeExecutionContext(operation_id=uuid4())

        result = execute_compute_pipeline(contract, "  hello  ", context)

        assert result.success is True
        # Disabled step not executed, so not uppercase
        assert result.output == "hello"
        assert "disabled_step" not in result.steps_executed
        assert "enabled_step" in result.steps_executed

    def test_empty_pipeline(self) -> None:
        """Test empty pipeline returns input unchanged."""
        contract = ModelComputeSubcontract(
            operation_name="empty",
            operation_version={"major": 1, "minor": 0, "patch": 0},
            pipeline=[],
        )
        context = ModelComputeExecutionContext(operation_id=uuid4())

        result = execute_compute_pipeline(contract, "input", context)

        assert result.success is True
        assert result.output == "input"
        assert result.steps_executed == []

    def test_pipeline_tracks_timing(self) -> None:
        """Test pipeline tracks processing time."""
        contract = ModelComputeSubcontract(
            operation_name="timed",
            operation_version={"major": 1, "minor": 0, "patch": 0},
            pipeline=[
                ModelComputePipelineStep(
                    step_name="step1",
                    step_type=EnumComputeStepType.TRANSFORMATION,
                    transformation_type=EnumTransformationType.IDENTITY,
                ),
            ],
        )
        context = ModelComputeExecutionContext(operation_id=uuid4())

        result = execute_compute_pipeline(contract, "data", context)

        assert result.success is True
        assert result.processing_time_ms >= 0
        assert result.step_results["step1"].metadata.duration_ms >= 0

    def test_regex_transformation_in_pipeline(self) -> None:
        """Test regex transformation in pipeline."""
        contract = ModelComputeSubcontract(
            operation_name="regex_clean",
            operation_version={"major": 1, "minor": 0, "patch": 0},
            pipeline=[
                ModelComputePipelineStep(
                    step_name="normalize_spaces",
                    step_type=EnumComputeStepType.TRANSFORMATION,
                    transformation_type=EnumTransformationType.REGEX,
                    transformation_config=ModelTransformRegexConfig(
                        pattern=r"\s+",
                        replacement=" ",
                    ),
                ),
            ],
        )
        context = ModelComputeExecutionContext(operation_id=uuid4())

        result = execute_compute_pipeline(contract, "hello   world", context)

        assert result.success is True
        assert result.output == "hello world"
