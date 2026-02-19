# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

#
# SPDX-License-Identifier: Apache-2.0
"""Tests for ModelHandlerSpec."""

import pytest
from pydantic import ValidationError

from omnibase_core.models.contracts.model_handler_spec import ModelHandlerSpec


@pytest.mark.unit
class TestModelHandlerSpec:
    """Tests for ModelHandlerSpec model."""

    @pytest.mark.unit
    def test_valid_handler_spec(self) -> None:
        """Test creating a valid handler spec."""
        spec = ModelHandlerSpec(
            name="http_client",
            handler_type="http",
        )
        assert spec.name == "http_client"
        assert spec.handler_type == "http"
        assert spec.import_path is None
        assert spec.config is None

    @pytest.mark.unit
    def test_full_handler_spec(self) -> None:
        """Test creating a handler spec with all fields."""
        spec = ModelHandlerSpec(
            name="kafka_producer",
            handler_type="kafka",
            import_path="mypackage.handlers.KafkaProducer",
            config={"bootstrap_servers": "localhost:9092", "retries": 3},
        )
        assert spec.name == "kafka_producer"
        assert spec.handler_type == "kafka"
        assert spec.import_path == "mypackage.handlers.KafkaProducer"
        assert spec.config == {"bootstrap_servers": "localhost:9092", "retries": 3}

    @pytest.mark.unit
    def test_name_required(self) -> None:
        """Test that name is required."""
        with pytest.raises(ValidationError):
            ModelHandlerSpec(handler_type="http")  # type: ignore[call-arg]

    @pytest.mark.unit
    def test_handler_type_required(self) -> None:
        """Test that handler_type is required."""
        with pytest.raises(ValidationError):
            ModelHandlerSpec(name="test")  # type: ignore[call-arg]

    @pytest.mark.unit
    def test_empty_name_rejected(self) -> None:
        """Test that empty name is rejected."""
        with pytest.raises(ValidationError):
            ModelHandlerSpec(name="", handler_type="http")

    @pytest.mark.unit
    def test_empty_handler_type_rejected(self) -> None:
        """Test that empty handler_type is rejected."""
        with pytest.raises(ValidationError):
            ModelHandlerSpec(name="test", handler_type="")

    @pytest.mark.unit
    def test_name_validation_valid_names(self) -> None:
        """Test name validation with valid names."""
        valid_names = [
            "http_client",
            "kafka_producer",
            "db_handler",
            "handler123",
            "my_handler_v2",
        ]
        for name in valid_names:
            spec = ModelHandlerSpec(name=name, handler_type="test")
            assert spec.name == name

    @pytest.mark.unit
    def test_name_validation_invalid_names(self) -> None:
        """Test name validation with invalid names."""
        invalid_names = [
            "http-client",  # Contains dash
            "handler.name",  # Contains dot
            "handler name",  # Contains space
            "handler@test",  # Contains special char
        ]
        for name in invalid_names:
            with pytest.raises(ValidationError):
                ModelHandlerSpec(name=name, handler_type="test")

    @pytest.mark.unit
    def test_handler_type_lowercased(self) -> None:
        """Test that handler_type is lowercased."""
        spec = ModelHandlerSpec(name="test", handler_type="HTTP")
        assert spec.handler_type == "http"

    @pytest.mark.unit
    def test_import_path_validation_valid(self) -> None:
        """Test import path validation with valid paths."""
        valid_paths = [
            "mypackage.Handler",
            "my.deep.module.Handler",
            "pkg.mod.MyHandler",
        ]
        for path in valid_paths:
            spec = ModelHandlerSpec(
                name="test",
                handler_type="test",
                import_path=path,
            )
            assert spec.import_path == path

    @pytest.mark.unit
    def test_import_path_validation_invalid(self) -> None:
        """Test import path validation with invalid paths."""
        with pytest.raises(ValidationError):
            ModelHandlerSpec(
                name="test",
                handler_type="test",
                import_path="single_segment",  # Must have module.class
            )

    @pytest.mark.unit
    def test_empty_import_path_becomes_none(self) -> None:
        """Test that empty import path becomes None."""
        spec = ModelHandlerSpec(
            name="test",
            handler_type="test",
            import_path="   ",
        )
        assert spec.import_path is None

    @pytest.mark.unit
    def test_config_accepts_various_types(self) -> None:
        """Test that config accepts supported value types."""
        config = {
            "string_val": "test",
            "int_val": 42,
            "float_val": 3.14,
            "bool_val": True,
            "list_val": ["a", "b", "c"],  # Only list[str] supported
            "null_val": None,
        }
        spec = ModelHandlerSpec(
            name="test",
            handler_type="test",
            config=config,
        )
        assert spec.config == config

    @pytest.mark.unit
    def test_extra_fields_rejected(self) -> None:
        """Test that extra fields are rejected."""
        with pytest.raises(ValidationError):
            ModelHandlerSpec(
                name="test",
                handler_type="test",
                extra="not_allowed",  # type: ignore[call-arg]
            )

    @pytest.mark.unit
    def test_frozen_model(self) -> None:
        """Test that the model is immutable."""
        spec = ModelHandlerSpec(name="test", handler_type="http")
        with pytest.raises(ValidationError):
            spec.name = "changed"  # type: ignore[misc]

    @pytest.mark.unit
    def test_repr(self) -> None:
        """Test string representation."""
        spec = ModelHandlerSpec(name="http_client", handler_type="http")
        repr_str = repr(spec)
        assert "http_client" in repr_str
        assert "http" in repr_str

    @pytest.mark.unit
    def test_equality(self) -> None:
        """Test equality comparison."""
        spec1 = ModelHandlerSpec(name="test", handler_type="http")
        spec2 = ModelHandlerSpec(name="test", handler_type="http")
        spec3 = ModelHandlerSpec(name="other", handler_type="http")
        assert spec1 == spec2
        assert spec1 != spec3

    @pytest.mark.unit
    def test_from_dict(self) -> None:
        """Test creating from dictionary."""
        data = {
            "name": "http_client",
            "handler_type": "http",
            "import_path": "mypackage.Handler",
            "config": {"timeout": 30},
        }
        spec = ModelHandlerSpec.model_validate(data)
        assert spec.name == "http_client"
        assert spec.handler_type == "http"
        assert spec.import_path == "mypackage.Handler"
        assert spec.config == {"timeout": 30}

    @pytest.mark.unit
    def test_whitespace_stripping(self) -> None:
        """Test that whitespace is stripped."""
        spec = ModelHandlerSpec(
            name="  http_client  ",
            handler_type="  http  ",
        )
        assert spec.name == "http_client"
        assert spec.handler_type == "http"

    @pytest.mark.unit
    def test_name_normalized_to_lowercase(self) -> None:
        """Test that handler name is normalized to lowercase for consistent matching."""
        spec = ModelHandlerSpec(
            name="HTTP_Client",
            handler_type="http",
        )
        assert spec.name == "http_client"

    @pytest.mark.unit
    def test_name_normalization_preserves_underscores(self) -> None:
        """Test that name normalization preserves underscores."""
        spec = ModelHandlerSpec(
            name="MyKafkaProducer_V2",
            handler_type="kafka",
        )
        assert spec.name == "mykafkaproducer_v2"

    @pytest.mark.unit
    def test_name_normalization_with_mixed_case(self) -> None:
        """Test that mixed case names are fully lowercased."""
        test_cases = [
            ("HttpClient", "httpclient"),
            ("HTTP_CLIENT", "http_client"),
            ("kafkaProducer", "kafkaproducer"),
            ("DB_Handler_V2", "db_handler_v2"),
        ]
        for input_name, expected_name in test_cases:
            spec = ModelHandlerSpec(name=input_name, handler_type="test")
            assert spec.name == expected_name, (
                f"Expected {expected_name} for {input_name}"
            )
