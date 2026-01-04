# SPDX-FileCopyrightText: 2025 OmniNode Team <info@omninode.ai>
#
# SPDX-License-Identifier: Apache-2.0
"""
Tests for ServiceConfigOverrideInjector.

Tests the configuration override injection service for OMN-1205.
Validates the service's ability to validate, preview, and apply configuration
overrides while maintaining immutability and thread-safety guarantees.

Test Categories:
    - TestValidate: Validation of override paths and types
    - TestPreview: Preview generation with before/after state
    - TestApply: Application of overrides with immutability guarantees
    - TestEnvironmentOverlay: Environment variable overlay generation
    - TestPathTraversal: Nested path handling (dicts, lists, models)
    - TestPydanticModelConfig: Pydantic model support
    - TestConcurrentAccess: Thread-safety verification

OMN-1205: Configuration Override Injection
"""

import concurrent.futures
import copy
import os
import threading
from typing import Any

import pytest
from pydantic import BaseModel, ConfigDict

from omnibase_core.enums.replay.enum_override_injection_point import (
    EnumOverrideInjectionPoint,
)
from omnibase_core.models.replay import (
    ModelConfigOverride,
    ModelConfigOverrideSet,
)
from omnibase_core.services.replay.service_config_override_injector import (
    MISSING,
    ServiceConfigOverrideInjector,
)

# =============================================================================
# FIXTURES
# =============================================================================


@pytest.fixture
def injector() -> ServiceConfigOverrideInjector:
    """Create a standard (non-strict) config override injector."""
    return ServiceConfigOverrideInjector()


@pytest.fixture
def strict_injector() -> ServiceConfigOverrideInjector:
    """Create a strict mode config override injector."""
    return ServiceConfigOverrideInjector(strict_mode=True)


@pytest.fixture
def sample_dict_config() -> dict[str, Any]:
    """Create a sample nested dictionary configuration."""
    return {
        "llm": {
            "openai": {"temperature": 0.9, "model": "gpt-4"},
            "max_tokens": 1000,
        },
        "retry": {"max_attempts": 5, "backoff_factor": 2.0},
        "debug": False,
    }


@pytest.fixture
def sample_overrides() -> ModelConfigOverrideSet:
    """Create a sample override set with two overrides."""
    return ModelConfigOverrideSet(
        overrides=(
            ModelConfigOverride(path="llm.openai.temperature", value=0.5),
            ModelConfigOverride(path="retry.max_attempts", value=3),
        )
    )


@pytest.fixture
def config_with_list() -> dict[str, Any]:
    """Create a configuration with list elements."""
    return {
        "items": [
            {"name": "first", "enabled": True},
            {"name": "second", "enabled": False},
            {"name": "third", "enabled": True},
        ],
        "tags": ["tag1", "tag2", "tag3"],
    }


class SamplePydanticConfig(BaseModel):
    """Sample Pydantic model for testing override application."""

    model_config = ConfigDict(extra="forbid")

    timeout: int = 30
    debug: bool = False
    name: str = "default"


class FrozenPydanticConfig(BaseModel):
    """Frozen Pydantic model for testing immutability."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    timeout: int = 30
    debug: bool = False


class NestedPydanticConfig(BaseModel):
    """Nested Pydantic model for testing deep paths."""

    model_config = ConfigDict(extra="forbid")

    inner: SamplePydanticConfig = SamplePydanticConfig()
    level: int = 1


# =============================================================================
# TEST VALIDATE
# =============================================================================


@pytest.mark.unit
class TestValidate:
    """Tests for the validate() method."""

    def test_validate_existing_paths_returns_valid(
        self,
        injector: ServiceConfigOverrideInjector,
        sample_dict_config: dict[str, Any],
        sample_overrides: ModelConfigOverrideSet,
    ) -> None:
        """Validate returns is_valid=True when all paths exist."""
        validation = injector.validate(sample_overrides, sample_dict_config)

        assert validation.is_valid is True
        assert len(validation.violations) == 0
        assert validation.paths_validated == 2
        assert validation.type_checks_passed == 2

    def test_validate_missing_path_non_strict_returns_warning(
        self,
        injector: ServiceConfigOverrideInjector,
        sample_dict_config: dict[str, Any],
    ) -> None:
        """Validate returns warning (not violation) for missing path in non-strict mode."""
        overrides = ModelConfigOverrideSet(
            overrides=(ModelConfigOverride(path="nonexistent.path", value="test"),)
        )

        validation = injector.validate(overrides, sample_dict_config)

        assert validation.is_valid is True  # Non-strict allows warnings
        assert len(validation.violations) == 0
        assert len(validation.warnings) == 1
        assert "nonexistent.path" in validation.warnings[0]
        assert "does not exist" in validation.warnings[0]

    def test_validate_missing_path_strict_returns_violation(
        self,
        strict_injector: ServiceConfigOverrideInjector,
        sample_dict_config: dict[str, Any],
    ) -> None:
        """Validate returns is_valid=False for missing path in strict mode."""
        overrides = ModelConfigOverrideSet(
            overrides=(ModelConfigOverride(path="nonexistent.path", value="test"),)
        )

        validation = strict_injector.validate(overrides, sample_dict_config)

        # Strict mode treats warnings as failures
        assert validation.is_valid is False
        assert len(validation.warnings) >= 1
        assert "nonexistent.path" in validation.warnings[0]

    def test_validate_type_mismatch_returns_warning(
        self,
        injector: ServiceConfigOverrideInjector,
        sample_dict_config: dict[str, Any],
    ) -> None:
        """Validate returns warning when override type doesn't match existing value."""
        overrides = ModelConfigOverrideSet(
            overrides=(
                # debug is bool, trying to set to string
                ModelConfigOverride(path="debug", value="not_a_bool"),
            )
        )

        validation = injector.validate(overrides, sample_dict_config)

        # Type mismatch produces warning, not violation (non-strict)
        assert validation.is_valid is True
        assert len(validation.warnings) >= 1
        assert any("Type mismatch" in w for w in validation.warnings)

    def test_validate_invalid_path_syntax(
        self,
        injector: ServiceConfigOverrideInjector,
        sample_dict_config: dict[str, Any],
    ) -> None:
        """Validate returns violation for invalid path syntax."""
        overrides = ModelConfigOverrideSet(
            overrides=(ModelConfigOverride(path="..invalid", value="test"),)
        )

        validation = injector.validate(overrides, sample_dict_config)

        assert validation.is_valid is False
        assert len(validation.violations) >= 1
        assert any("Invalid path syntax" in v for v in validation.violations)

    def test_validate_numeric_conversion_allowed(
        self,
        injector: ServiceConfigOverrideInjector,
        sample_dict_config: dict[str, Any],
    ) -> None:
        """Validate allows int/float conversion without warning."""
        overrides = ModelConfigOverrideSet(
            overrides=(
                # max_tokens is int (1000), setting to float
                ModelConfigOverride(path="llm.max_tokens", value=1500.0),
            )
        )

        validation = injector.validate(overrides, sample_dict_config)

        assert validation.is_valid is True
        # Numeric conversion is acceptable, should pass type check
        assert validation.type_checks_passed == 1


# =============================================================================
# TEST PREVIEW
# =============================================================================


@pytest.mark.unit
class TestPreview:
    """Tests for the preview() method."""

    def test_preview_shows_before_after(
        self,
        injector: ServiceConfigOverrideInjector,
        sample_dict_config: dict[str, Any],
        sample_overrides: ModelConfigOverrideSet,
    ) -> None:
        """Preview shows old and new values for each override."""
        preview = injector.preview(sample_overrides, sample_dict_config)

        assert len(preview.field_previews) == 2

        # Check temperature override
        temp_preview = next(
            p for p in preview.field_previews if p.path == "llm.openai.temperature"
        )
        assert temp_preview.old_value == 0.9
        assert temp_preview.new_value == 0.5
        assert temp_preview.path_exists is True

        # Check retry override
        retry_preview = next(
            p for p in preview.field_previews if p.path == "retry.max_attempts"
        )
        assert retry_preview.old_value == 5
        assert retry_preview.new_value == 3
        assert retry_preview.path_exists is True

    def test_preview_identifies_new_paths(
        self,
        injector: ServiceConfigOverrideInjector,
        sample_dict_config: dict[str, Any],
    ) -> None:
        """Preview identifies paths that don't exist (will be created)."""
        overrides = ModelConfigOverrideSet(
            overrides=(
                ModelConfigOverride(path="new_setting", value="new_value"),
                ModelConfigOverride(path="another.new.path", value=123),
            )
        )

        preview = injector.preview(overrides, sample_dict_config)

        assert len(preview.paths_not_found) == 2
        assert "new_setting" in preview.paths_not_found
        assert "another.new.path" in preview.paths_not_found

        # Field previews should show path_exists=False
        for fp in preview.field_previews:
            assert fp.path_exists is False

    def test_preview_to_markdown_generates_table(
        self,
        injector: ServiceConfigOverrideInjector,
        sample_dict_config: dict[str, Any],
        sample_overrides: ModelConfigOverrideSet,
    ) -> None:
        """Preview to_markdown() generates valid markdown table."""
        preview = injector.preview(sample_overrides, sample_dict_config)
        markdown = preview.to_markdown()

        # Check header
        assert "## Configuration Override Preview" in markdown
        assert "| Path | Injection Point | Before | After | Status |" in markdown
        assert "|------|-----------------|--------|-------|--------|" in markdown

        # Check content
        assert "llm.openai.temperature" in markdown
        assert "retry.max_attempts" in markdown

    def test_preview_type_mismatches_tracked(
        self,
        injector: ServiceConfigOverrideInjector,
        sample_dict_config: dict[str, Any],
    ) -> None:
        """Preview tracks type mismatches for review."""
        overrides = ModelConfigOverrideSet(
            overrides=(ModelConfigOverride(path="debug", value="string_not_bool"),)
        )

        preview = injector.preview(overrides, sample_dict_config)

        assert len(preview.type_mismatches) == 1
        assert "debug" in preview.type_mismatches[0]


# =============================================================================
# TEST APPLY
# =============================================================================


@pytest.mark.unit
class TestApply:
    """Tests for the apply() method - critical immutability tests."""

    def test_apply_does_not_modify_original(
        self,
        injector: ServiceConfigOverrideInjector,
        sample_dict_config: dict[str, Any],
        sample_overrides: ModelConfigOverrideSet,
    ) -> None:
        """Apply NEVER modifies the original configuration."""
        original_copy = copy.deepcopy(sample_dict_config)

        result = injector.apply(sample_overrides, sample_dict_config)

        # Original must remain unchanged
        assert sample_dict_config == original_copy
        assert sample_dict_config["llm"]["openai"]["temperature"] == 0.9
        assert sample_dict_config["retry"]["max_attempts"] == 5

        # Patched config should have new values
        assert result.patched_config["llm"]["openai"]["temperature"] == 0.5
        assert result.patched_config["retry"]["max_attempts"] == 3

    def test_apply_returns_new_object(
        self,
        injector: ServiceConfigOverrideInjector,
        sample_dict_config: dict[str, Any],
        sample_overrides: ModelConfigOverrideSet,
    ) -> None:
        """Apply returns a new object, not the original."""
        result = injector.apply(sample_overrides, sample_dict_config)

        assert result.patched_config is not sample_dict_config
        assert result.patched_config["llm"] is not sample_dict_config["llm"]
        assert (
            result.patched_config["llm"]["openai"]
            is not sample_dict_config["llm"]["openai"]
        )

    def test_apply_preserves_unspecified_fields(
        self,
        injector: ServiceConfigOverrideInjector,
        sample_dict_config: dict[str, Any],
    ) -> None:
        """Apply preserves fields not specified in overrides."""
        overrides = ModelConfigOverrideSet(
            overrides=(ModelConfigOverride(path="llm.openai.temperature", value=0.1),)
        )

        result = injector.apply(overrides, sample_dict_config)

        # Modified field
        assert result.patched_config["llm"]["openai"]["temperature"] == 0.1

        # Preserved fields
        assert result.patched_config["llm"]["openai"]["model"] == "gpt-4"
        assert result.patched_config["llm"]["max_tokens"] == 1000
        assert result.patched_config["retry"]["max_attempts"] == 5
        assert result.patched_config["retry"]["backoff_factor"] == 2.0
        assert result.patched_config["debug"] is False

    def test_apply_tracks_created_paths(
        self,
        injector: ServiceConfigOverrideInjector,
        sample_dict_config: dict[str, Any],
    ) -> None:
        """Apply tracks paths that were created (didn't exist before)."""
        overrides = ModelConfigOverrideSet(
            overrides=(
                ModelConfigOverride(path="new_setting", value="created"),
                ModelConfigOverride(path="llm.openai.temperature", value=0.5),
            )
        )

        result = injector.apply(overrides, sample_dict_config)

        assert result.success is True
        assert "new_setting" in result.paths_created
        # temperature existed, should not be in paths_created
        assert "llm.openai.temperature" not in result.paths_created
        assert result.overrides_applied == 2

    def test_apply_reports_errors_for_invalid_paths(
        self,
        injector: ServiceConfigOverrideInjector,
        sample_dict_config: dict[str, Any],
    ) -> None:
        """Apply reports errors for invalid path syntax."""
        overrides = ModelConfigOverrideSet(
            overrides=(ModelConfigOverride(path="..bad.path", value="test"),)
        )

        result = injector.apply(overrides, sample_dict_config)

        assert result.success is False
        assert len(result.errors) >= 1
        assert any("Invalid path" in e for e in result.errors)


# =============================================================================
# TEST ENVIRONMENT OVERLAY
# =============================================================================


@pytest.mark.unit
class TestEnvironmentOverlay:
    """Tests for the apply_environment_overlay() method."""

    def test_creates_env_dict_not_modifying_os_environ(
        self,
        injector: ServiceConfigOverrideInjector,
    ) -> None:
        """Environment overlay creates dict without touching os.environ."""
        original_environ = dict(os.environ)

        overrides = ModelConfigOverrideSet(
            overrides=(
                ModelConfigOverride(
                    path="test_var",
                    value="test_value",
                    injection_point=EnumOverrideInjectionPoint.ENVIRONMENT,
                ),
                ModelConfigOverride(
                    path="api.key",
                    value="secret123",
                    injection_point=EnumOverrideInjectionPoint.ENVIRONMENT,
                ),
            )
        )

        overlay = injector.apply_environment_overlay(overrides)

        # os.environ must remain unchanged
        assert dict(os.environ) == original_environ

        # Overlay should contain the environment variables
        assert "TEST_VAR" in overlay or "test_var" in overlay
        assert "KEY" in overlay  # Last segment, uppercased

    def test_env_overlay_only_includes_environment_injection_point(
        self,
        injector: ServiceConfigOverrideInjector,
    ) -> None:
        """Environment overlay only includes ENVIRONMENT injection point overrides."""
        overrides = ModelConfigOverrideSet(
            overrides=(
                ModelConfigOverride(
                    path="env_var",
                    value="included",
                    injection_point=EnumOverrideInjectionPoint.ENVIRONMENT,
                ),
                ModelConfigOverride(
                    path="handler_var",
                    value="excluded",
                    injection_point=EnumOverrideInjectionPoint.HANDLER_CONFIG,
                ),
            )
        )

        overlay = injector.apply_environment_overlay(overrides)

        assert len(overlay) == 1
        assert "ENV_VAR" in overlay

    def test_env_overlay_converts_values_to_strings(
        self,
        injector: ServiceConfigOverrideInjector,
    ) -> None:
        """Environment overlay converts all values to strings."""
        overrides = ModelConfigOverrideSet(
            overrides=(
                ModelConfigOverride(
                    path="int_var",
                    value=42,
                    injection_point=EnumOverrideInjectionPoint.ENVIRONMENT,
                ),
                ModelConfigOverride(
                    path="bool_var",
                    value=True,
                    injection_point=EnumOverrideInjectionPoint.ENVIRONMENT,
                ),
                ModelConfigOverride(
                    path="none_var",
                    value=None,
                    injection_point=EnumOverrideInjectionPoint.ENVIRONMENT,
                ),
            )
        )

        overlay = injector.apply_environment_overlay(overrides)

        assert overlay["INT_VAR"] == "42"
        assert overlay["BOOL_VAR"] == "true"
        assert overlay["NONE_VAR"] == ""


# =============================================================================
# TEST PATH TRAVERSAL
# =============================================================================


@pytest.mark.unit
class TestPathTraversal:
    """Tests for nested path handling."""

    def test_deep_nested_path(
        self,
        injector: ServiceConfigOverrideInjector,
    ) -> None:
        """Handles deeply nested paths like a.b.c.d."""
        config: dict[str, Any] = {"a": {"b": {"c": {"d": {"value": "original"}}}}}
        overrides = ModelConfigOverrideSet(
            overrides=(ModelConfigOverride(path="a.b.c.d.value", value="modified"),)
        )

        result = injector.apply(overrides, config)

        assert result.success is True
        assert result.patched_config["a"]["b"]["c"]["d"]["value"] == "modified"
        # Original unchanged
        assert config["a"]["b"]["c"]["d"]["value"] == "original"

    def test_list_index_path(
        self,
        injector: ServiceConfigOverrideInjector,
        config_with_list: dict[str, Any],
    ) -> None:
        """Handles list index paths like items.0.name."""
        overrides = ModelConfigOverrideSet(
            overrides=(
                ModelConfigOverride(path="items.0.name", value="modified_first"),
                ModelConfigOverride(path="items.1.enabled", value=True),
                ModelConfigOverride(path="tags.2", value="modified_tag"),
            )
        )

        result = injector.apply(overrides, config_with_list)

        assert result.success is True
        assert result.patched_config["items"][0]["name"] == "modified_first"
        assert result.patched_config["items"][1]["enabled"] is True
        assert result.patched_config["tags"][2] == "modified_tag"

        # Original unchanged
        assert config_with_list["items"][0]["name"] == "first"
        assert config_with_list["items"][1]["enabled"] is False
        assert config_with_list["tags"][2] == "tag3"

    def test_list_index_out_of_bounds(
        self,
        injector: ServiceConfigOverrideInjector,
        config_with_list: dict[str, Any],
    ) -> None:
        """Handles out-of-bounds list index gracefully."""
        overrides = ModelConfigOverrideSet(
            overrides=(ModelConfigOverride(path="items.99.name", value="test"),)
        )

        result = injector.apply(overrides, config_with_list)

        assert result.success is False
        assert len(result.errors) >= 1
        assert any("out of bounds" in e.lower() for e in result.errors)

    def test_create_intermediate_dicts(
        self,
        injector: ServiceConfigOverrideInjector,
    ) -> None:
        """Creates intermediate dictionaries when path doesn't exist."""
        config: dict[str, Any] = {"existing": "value"}
        overrides = ModelConfigOverrideSet(
            overrides=(ModelConfigOverride(path="new.nested.path", value="created"),)
        )

        result = injector.apply(overrides, config)

        assert result.success is True
        assert result.patched_config["new"]["nested"]["path"] == "created"
        assert "new.nested.path" in result.paths_created


# =============================================================================
# TEST PYDANTIC MODEL CONFIG
# =============================================================================


@pytest.mark.unit
class TestPydanticModelConfig:
    """Tests for Pydantic model support."""

    def test_apply_to_pydantic_model(
        self,
        injector: ServiceConfigOverrideInjector,
    ) -> None:
        """Apply works with mutable Pydantic models."""
        config = SamplePydanticConfig(timeout=30, debug=False, name="original")
        overrides = ModelConfigOverrideSet(
            overrides=(
                ModelConfigOverride(path="timeout", value=60),
                ModelConfigOverride(path="name", value="modified"),
            )
        )

        result = injector.apply(overrides, config)

        assert result.success is True
        assert result.patched_config.timeout == 60
        assert result.patched_config.name == "modified"
        assert result.patched_config.debug is False  # Preserved

        # Original unchanged (Pydantic model_copy creates new instance)
        assert config.timeout == 30
        assert config.name == "original"

    def test_apply_to_frozen_pydantic_model_fails_gracefully(
        self,
        injector: ServiceConfigOverrideInjector,
    ) -> None:
        """Apply handles frozen Pydantic models appropriately."""
        config = FrozenPydanticConfig(timeout=30, debug=False)
        overrides = ModelConfigOverrideSet(
            overrides=(ModelConfigOverride(path="timeout", value=60),)
        )

        result = injector.apply(overrides, config)

        # Frozen models can't be modified in place
        # The service should report an error
        assert result.success is False
        assert len(result.errors) >= 1

    def test_validate_pydantic_model_paths(
        self,
        injector: ServiceConfigOverrideInjector,
    ) -> None:
        """Validate works with Pydantic model paths."""
        config = SamplePydanticConfig(timeout=30)
        overrides = ModelConfigOverrideSet(
            overrides=(
                ModelConfigOverride(path="timeout", value=60),
                ModelConfigOverride(path="nonexistent", value="test"),
            )
        )

        validation = injector.validate(overrides, config)

        # First override is valid
        # Second doesn't exist - warning
        assert len(validation.warnings) >= 1
        assert any("nonexistent" in w for w in validation.warnings)

    def test_apply_to_nested_pydantic_model(
        self,
        injector: ServiceConfigOverrideInjector,
    ) -> None:
        """Apply handles nested Pydantic models."""
        config = NestedPydanticConfig()
        overrides = ModelConfigOverrideSet(
            overrides=(
                ModelConfigOverride(path="inner.timeout", value=120),
                ModelConfigOverride(path="level", value=5),
            )
        )

        result = injector.apply(overrides, config)

        assert result.success is True
        assert result.patched_config.inner.timeout == 120
        assert result.patched_config.level == 5


# =============================================================================
# TEST CONCURRENT ACCESS
# =============================================================================


@pytest.mark.unit
class TestConcurrentAccess:
    """Tests for thread-safety."""

    def test_concurrent_apply_no_race_condition(
        self,
        injector: ServiceConfigOverrideInjector,
    ) -> None:
        """Multiple concurrent applies don't cause race conditions."""
        config: dict[str, Any] = {"shared": {"counter": 0}, "value": "original"}

        results: list[Any] = []
        errors: list[Exception] = []
        lock = threading.Lock()

        def apply_override(index: int) -> None:
            """Apply an override and store result."""
            try:
                overrides = ModelConfigOverrideSet(
                    overrides=(
                        ModelConfigOverride(path="value", value=f"modified_{index}"),
                        ModelConfigOverride(path=f"new_field_{index}", value=index),
                    )
                )
                result = injector.apply(overrides, config)
                with lock:
                    results.append((index, result))
            except Exception as e:
                with lock:
                    errors.append(e)

        # Run concurrent applies
        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(apply_override, i) for i in range(20)]
            concurrent.futures.wait(futures)

        # No errors should occur
        assert len(errors) == 0, f"Errors occurred: {errors}"

        # All applies should succeed
        assert len(results) == 20

        # Original config must be unchanged
        assert config["value"] == "original"
        assert config["shared"]["counter"] == 0
        assert "new_field_0" not in config

        # Each result should have independent patched config
        for index, result in results:
            assert result.success is True
            assert result.patched_config["value"] == f"modified_{index}"
            assert result.patched_config[f"new_field_{index}"] == index

    def test_concurrent_validate_no_race_condition(
        self,
        injector: ServiceConfigOverrideInjector,
    ) -> None:
        """Multiple concurrent validates are thread-safe."""
        config: dict[str, Any] = {"field1": "value1", "field2": 100}

        results: list[Any] = []
        lock = threading.Lock()

        def validate_override(index: int) -> None:
            """Validate an override and store result."""
            overrides = ModelConfigOverrideSet(
                overrides=(
                    ModelConfigOverride(path="field1", value=f"new_{index}"),
                    ModelConfigOverride(path="field2", value=index),
                )
            )
            validation = injector.validate(overrides, config)
            with lock:
                results.append((index, validation))

        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(validate_override, i) for i in range(20)]
            concurrent.futures.wait(futures)

        # All validations should succeed
        assert len(results) == 20
        for _, validation in results:
            assert validation.is_valid is True
            assert validation.paths_validated == 2

    def test_injector_instance_reuse_thread_safe(
        self,
    ) -> None:
        """Single injector instance can be safely reused across threads."""
        injector = ServiceConfigOverrideInjector()
        configs = [{"value": i} for i in range(10)]

        results: list[Any] = []
        lock = threading.Lock()

        def process_config(config: dict[str, Any], index: int) -> None:
            """Process a config with the shared injector."""
            overrides = ModelConfigOverrideSet(
                overrides=(ModelConfigOverride(path="value", value=index * 10),)
            )
            result = injector.apply(overrides, config)
            with lock:
                results.append((config["value"], result.patched_config["value"]))

        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            futures = [
                executor.submit(process_config, configs[i], i) for i in range(10)
            ]
            concurrent.futures.wait(futures)

        assert len(results) == 10

        # Verify each original config retained its value
        for i in range(10):
            assert configs[i]["value"] == i


# =============================================================================
# TEST EDGE CASES
# =============================================================================


@pytest.mark.unit
class TestEdgeCases:
    """Tests for edge cases and boundary conditions."""

    def test_empty_override_set(
        self,
        injector: ServiceConfigOverrideInjector,
        sample_dict_config: dict[str, Any],
    ) -> None:
        """Handles empty override set gracefully."""
        overrides = ModelConfigOverrideSet(overrides=())

        validation = injector.validate(overrides, sample_dict_config)
        assert validation.is_valid is True
        assert validation.paths_validated == 0

        preview = injector.preview(overrides, sample_dict_config)
        assert len(preview.field_previews) == 0

        result = injector.apply(overrides, sample_dict_config)
        assert result.success is True
        assert result.overrides_applied == 0
        assert result.patched_config == sample_dict_config

    def test_none_value_override(
        self,
        injector: ServiceConfigOverrideInjector,
        sample_dict_config: dict[str, Any],
    ) -> None:
        """Handles setting values to None."""
        overrides = ModelConfigOverrideSet(
            overrides=(ModelConfigOverride(path="llm.openai.temperature", value=None),)
        )

        result = injector.apply(overrides, sample_dict_config)

        assert result.success is True
        assert result.patched_config["llm"]["openai"]["temperature"] is None

    def test_missing_sentinel_behavior(
        self,
        injector: ServiceConfigOverrideInjector,
    ) -> None:
        """MISSING sentinel is distinct from None."""
        assert MISSING is not None
        assert bool(MISSING) is False
        assert repr(MISSING) == "<MISSING>"

        # Same instance always
        from omnibase_core.services.replay.service_config_override_injector import (
            _Missing,
        )

        assert _Missing() is MISSING

    def test_injection_point_filtering(
        self,
        injector: ServiceConfigOverrideInjector,
        sample_dict_config: dict[str, Any],
    ) -> None:
        """Filtering by injection point works correctly."""
        overrides = ModelConfigOverrideSet(
            overrides=(
                ModelConfigOverride(
                    path="llm.openai.temperature",
                    value=0.5,
                    injection_point=EnumOverrideInjectionPoint.HANDLER_CONFIG,
                ),
                ModelConfigOverride(
                    path="env_var",
                    value="test",
                    injection_point=EnumOverrideInjectionPoint.ENVIRONMENT,
                ),
            )
        )

        # Only validate HANDLER_CONFIG
        validation = injector.validate(
            overrides,
            sample_dict_config,
            injection_point=EnumOverrideInjectionPoint.HANDLER_CONFIG,
        )
        assert validation.paths_validated == 1

        # Only apply HANDLER_CONFIG
        result = injector.apply(
            overrides,
            sample_dict_config,
            injection_point=EnumOverrideInjectionPoint.HANDLER_CONFIG,
        )
        assert result.overrides_applied == 1
        assert result.patched_config["llm"]["openai"]["temperature"] == 0.5

    def test_path_depth_limit(
        self,
        injector: ServiceConfigOverrideInjector,
    ) -> None:
        """Path depth is limited to prevent DoS."""
        # Create a path exceeding MAX_PATH_DEPTH (20)
        deep_path = ".".join([f"level{i}" for i in range(25)])
        overrides = ModelConfigOverrideSet(
            overrides=(ModelConfigOverride(path=deep_path, value="test"),)
        )

        validation = injector.validate(overrides, {})

        assert validation.is_valid is False
        assert any("depth" in v.lower() for v in validation.violations)
