"""Unit tests for Contract-Driven NodeCompute v1.0 transformation configs."""

import pytest
from pydantic import ValidationError

from omnibase_core.enums.enum_case_mode import EnumCaseMode
from omnibase_core.enums.enum_regex_flag import EnumRegexFlag
from omnibase_core.enums.enum_trim_mode import EnumTrimMode
from omnibase_core.enums.enum_unicode_form import EnumUnicodeForm
from omnibase_core.models.transformations.model_mapping_config import ModelMappingConfig
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
from omnibase_core.models.transformations.model_validation_step_config import (
    ModelValidationStepConfig,
)


@pytest.mark.unit
@pytest.mark.timeout(30)
class TestModelTransformRegexConfig:
    """Tests for ModelTransformRegexConfig."""

    def test_create_minimal(self) -> None:
        """Test creating config with minimal fields."""
        config = ModelTransformRegexConfig(pattern=r"\s+")
        assert config.config_type == "regex"
        assert config.pattern == r"\s+"
        assert config.replacement == ""
        assert config.flags == []

    def test_create_full(self) -> None:
        """Test creating config with all fields."""
        config = ModelTransformRegexConfig(
            pattern=r"[a-z]+",
            replacement="X",
            flags=[EnumRegexFlag.IGNORECASE, EnumRegexFlag.MULTILINE],
        )
        assert config.replacement == "X"
        assert len(config.flags) == 2

    def test_rejects_extra_fields(self) -> None:
        """Test that extra fields are rejected."""
        with pytest.raises(ValidationError):
            ModelTransformRegexConfig(pattern=r"\d+", extra_field="bad")  # type: ignore[call-arg]

    def test_is_frozen(self) -> None:
        """Test that model is immutable."""
        config = ModelTransformRegexConfig(pattern=r"\d+")
        with pytest.raises(ValidationError, match="frozen"):
            config.pattern = r"\w+"  # type: ignore[misc]


@pytest.mark.unit
@pytest.mark.timeout(30)
class TestModelTransformCaseConfig:
    """Tests for ModelTransformCaseConfig."""

    def test_create_upper(self) -> None:
        """Test creating uppercase config."""
        config = ModelTransformCaseConfig(mode=EnumCaseMode.UPPER)
        assert config.config_type == "case_conversion"
        assert config.mode == EnumCaseMode.UPPER

    def test_create_lower(self) -> None:
        """Test creating lowercase config."""
        config = ModelTransformCaseConfig(mode=EnumCaseMode.LOWER)
        assert config.mode == EnumCaseMode.LOWER

    def test_create_title(self) -> None:
        """Test creating titlecase config."""
        config = ModelTransformCaseConfig(mode=EnumCaseMode.TITLE)
        assert config.mode == EnumCaseMode.TITLE

    def test_rejects_extra_fields(self) -> None:
        """Test that extra fields are rejected."""
        with pytest.raises(ValidationError):
            ModelTransformCaseConfig(mode=EnumCaseMode.UPPER, extra="bad")  # type: ignore[call-arg]


@pytest.mark.unit
@pytest.mark.timeout(30)
class TestModelTransformTrimConfig:
    """Tests for ModelTransformTrimConfig."""

    def test_default_mode(self) -> None:
        """Test default mode is BOTH."""
        config = ModelTransformTrimConfig()
        assert config.config_type == "trim"
        assert config.mode == EnumTrimMode.BOTH

    def test_create_left(self) -> None:
        """Test creating left trim config."""
        config = ModelTransformTrimConfig(mode=EnumTrimMode.LEFT)
        assert config.mode == EnumTrimMode.LEFT

    def test_create_right(self) -> None:
        """Test creating right trim config."""
        config = ModelTransformTrimConfig(mode=EnumTrimMode.RIGHT)
        assert config.mode == EnumTrimMode.RIGHT


@pytest.mark.unit
@pytest.mark.timeout(30)
class TestModelTransformUnicodeConfig:
    """Tests for ModelTransformUnicodeConfig."""

    def test_default_form(self) -> None:
        """Test default form is NFC."""
        config = ModelTransformUnicodeConfig()
        assert config.config_type == "normalize_unicode"
        assert config.form == EnumUnicodeForm.NFC

    def test_create_nfd(self) -> None:
        """Test creating NFD config."""
        config = ModelTransformUnicodeConfig(form=EnumUnicodeForm.NFD)
        assert config.form == EnumUnicodeForm.NFD

    def test_create_nfkc(self) -> None:
        """Test creating NFKC config."""
        config = ModelTransformUnicodeConfig(form=EnumUnicodeForm.NFKC)
        assert config.form == EnumUnicodeForm.NFKC


@pytest.mark.unit
@pytest.mark.timeout(30)
class TestModelTransformJsonPathConfig:
    """Tests for ModelTransformJsonPathConfig."""

    def test_create(self) -> None:
        """Test creating JSONPath config."""
        config = ModelTransformJsonPathConfig(path="$.data.items")
        assert config.config_type == "json_path"
        assert config.path == "$.data.items"

    def test_path_root_only(self) -> None:
        """Test that root-only path is valid."""
        config = ModelTransformJsonPathConfig(path="$")
        assert config.path == "$"

    def test_path_empty_raises_error(self) -> None:
        """Test that empty path raises validation error."""
        with pytest.raises(ValueError, match="path cannot be empty"):
            ModelTransformJsonPathConfig(path="")

    def test_path_whitespace_only_raises_error(self) -> None:
        """Test that whitespace-only path raises validation error."""
        with pytest.raises(ValueError, match="path cannot be empty"):
            ModelTransformJsonPathConfig(path="   ")

    def test_path_without_dollar_raises_error(self) -> None:
        """Test that path not starting with $ raises validation error."""
        with pytest.raises(ValueError, match="path must start with"):
            ModelTransformJsonPathConfig(path="data.items")

    def test_path_with_dot_but_no_dollar_raises_error(self) -> None:
        """Test that path starting with dot raises validation error."""
        with pytest.raises(ValueError, match="path must start with"):
            ModelTransformJsonPathConfig(path=".data")

    def test_rejects_extra_fields(self) -> None:
        """Test that extra fields are rejected."""
        with pytest.raises(ValidationError):
            ModelTransformJsonPathConfig(path="$.x", extra="bad")  # type: ignore[call-arg]


@pytest.mark.unit
@pytest.mark.timeout(30)
class TestModelMappingConfig:
    """Tests for ModelMappingConfig."""

    def test_create(self) -> None:
        """Test creating mapping config."""
        config = ModelMappingConfig(
            field_mappings={
                "result": "$.steps.transform.output",
                "original": "$.input.text",
            }
        )
        assert config.config_type == "mapping"
        assert len(config.field_mappings) == 2
        assert config.field_mappings["result"] == "$.steps.transform.output"

    def test_empty_mappings_raises_error(self) -> None:
        """Test that empty field_mappings raises validation error."""
        import pytest

        with pytest.raises(ValueError, match="field_mappings cannot be empty"):
            ModelMappingConfig(field_mappings={})


@pytest.mark.unit
@pytest.mark.timeout(30)
class TestModelValidationStepConfig:
    """Tests for ModelValidationStepConfig."""

    def test_create_minimal(self) -> None:
        """Test creating config with minimal fields."""
        config = ModelValidationStepConfig(schema_ref="input_schema")
        assert config.config_type == "validation"
        assert config.schema_ref == "input_schema"
        assert config.fail_on_error is True  # default

    def test_create_full(self) -> None:
        """Test creating config with all fields."""
        config = ModelValidationStepConfig(
            schema_ref="my_schema_v1",
            fail_on_error=False,
        )
        assert config.schema_ref == "my_schema_v1"
        assert config.fail_on_error is False
