# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

#
# SPDX-License-Identifier: Apache-2.0
"""Unit tests for ModelExportOptions (OMN-1200)."""

import pytest
from pydantic import ValidationError


@pytest.mark.unit
class TestModelExportOptionsDefaults:
    """Tests for ModelExportOptions default values."""

    def test_default_values(self) -> None:
        """Default options should have expected values."""
        from omnibase_core.models.evidence.model_export_options import (
            ModelExportOptions,
        )

        options = ModelExportOptions()
        assert options.include_raw_data is False
        assert options.include_timestamps is True
        assert options.max_examples == 5
        assert options.verbose is False
        assert options.color_enabled is True
        assert options.indent_size == 2


@pytest.mark.unit
class TestModelExportOptionsCustomValues:
    """Tests for ModelExportOptions custom values."""

    def test_custom_values(self) -> None:
        """Custom values should be accepted."""
        from omnibase_core.models.evidence.model_export_options import (
            ModelExportOptions,
        )

        options = ModelExportOptions(
            include_raw_data=True,
            include_timestamps=False,
            max_examples=10,
            verbose=True,
            color_enabled=False,
            indent_size=4,
        )
        assert options.include_raw_data is True
        assert options.include_timestamps is False
        assert options.max_examples == 10
        assert options.verbose is True
        assert options.color_enabled is False
        assert options.indent_size == 4


@pytest.mark.unit
class TestModelExportOptionsValidation:
    """Tests for ModelExportOptions field validation."""

    def test_max_examples_validation_valid_min(self) -> None:
        """max_examples should accept minimum value 0."""
        from omnibase_core.models.evidence.model_export_options import (
            ModelExportOptions,
        )

        options = ModelExportOptions(max_examples=0)
        assert options.max_examples == 0

    def test_max_examples_validation_valid_max(self) -> None:
        """max_examples should accept maximum value 100."""
        from omnibase_core.models.evidence.model_export_options import (
            ModelExportOptions,
        )

        options = ModelExportOptions(max_examples=100)
        assert options.max_examples == 100

    def test_max_examples_validation_invalid_below_min(self) -> None:
        """max_examples should reject values below minimum."""
        from omnibase_core.models.evidence.model_export_options import (
            ModelExportOptions,
        )

        with pytest.raises(ValidationError):
            ModelExportOptions(max_examples=-1)

    def test_max_examples_validation_invalid_above_max(self) -> None:
        """max_examples should reject values above maximum."""
        from omnibase_core.models.evidence.model_export_options import (
            ModelExportOptions,
        )

        with pytest.raises(ValidationError):
            ModelExportOptions(max_examples=101)

    def test_indent_size_validation_valid_min(self) -> None:
        """indent_size should accept minimum value 0."""
        from omnibase_core.models.evidence.model_export_options import (
            ModelExportOptions,
        )

        options = ModelExportOptions(indent_size=0)
        assert options.indent_size == 0

    def test_indent_size_validation_valid_max(self) -> None:
        """indent_size should accept maximum value 8."""
        from omnibase_core.models.evidence.model_export_options import (
            ModelExportOptions,
        )

        options = ModelExportOptions(indent_size=8)
        assert options.indent_size == 8

    def test_indent_size_validation_invalid_above_max(self) -> None:
        """indent_size should reject values above maximum."""
        from omnibase_core.models.evidence.model_export_options import (
            ModelExportOptions,
        )

        with pytest.raises(ValidationError):
            ModelExportOptions(indent_size=9)

    def test_indent_size_validation_invalid_below_min(self) -> None:
        """indent_size should reject values below minimum."""
        from omnibase_core.models.evidence.model_export_options import (
            ModelExportOptions,
        )

        with pytest.raises(ValidationError):
            ModelExportOptions(indent_size=-1)


@pytest.mark.unit
class TestModelExportOptionsImmutability:
    """Tests for ModelExportOptions immutability."""

    def test_frozen_model(self) -> None:
        """Model should be immutable."""
        from omnibase_core.models.evidence.model_export_options import (
            ModelExportOptions,
        )

        options = ModelExportOptions()
        with pytest.raises(ValidationError):
            options.verbose = True  # type: ignore[misc]

    def test_frozen_model_include_raw_data(self) -> None:
        """include_raw_data should not be mutable."""
        from omnibase_core.models.evidence.model_export_options import (
            ModelExportOptions,
        )

        options = ModelExportOptions()
        with pytest.raises(ValidationError):
            options.include_raw_data = True  # type: ignore[misc]


@pytest.mark.unit
class TestModelExportOptionsExtraFields:
    """Tests for ModelExportOptions extra field handling."""

    def test_extra_fields_forbidden(self) -> None:
        """Extra fields should be rejected."""
        from omnibase_core.models.evidence.model_export_options import (
            ModelExportOptions,
        )

        with pytest.raises(ValidationError):
            ModelExportOptions(unknown_field=True)  # type: ignore[call-arg]


@pytest.mark.unit
class TestModelExportOptionsSerialization:
    """Tests for ModelExportOptions serialization."""

    def test_model_dump(self) -> None:
        """Model can be serialized to dict."""
        from omnibase_core.models.evidence.model_export_options import (
            ModelExportOptions,
        )

        options = ModelExportOptions(
            include_raw_data=True,
            max_examples=10,
        )

        data = options.model_dump()

        assert data["include_raw_data"] is True
        assert data["max_examples"] == 10
        assert data["verbose"] is False
        assert data["color_enabled"] is True

    def test_model_validate_from_dict(self) -> None:
        """Model can be created from dict."""
        from omnibase_core.models.evidence.model_export_options import (
            ModelExportOptions,
        )

        data = {
            "include_raw_data": True,
            "include_timestamps": False,
            "max_examples": 20,
            "verbose": True,
            "color_enabled": False,
            "indent_size": 4,
        }

        options = ModelExportOptions.model_validate(data)

        assert options.include_raw_data is True
        assert options.include_timestamps is False
        assert options.max_examples == 20
        assert options.verbose is True
        assert options.color_enabled is False
        assert options.indent_size == 4
