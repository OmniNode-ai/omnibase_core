# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Tests for ModelStepVerification."""

import pytest
from pydantic import ValidationError

from omnibase_core.models.orchestrator import ModelStepVerification


class TestModelStepVerification:
    """Tests for ModelStepVerification construction, serialization, and validation."""

    def test_construct_command_exit_0(self) -> None:
        v = ModelStepVerification(
            check_type="command_exit_0",
            target="uv --version",
            description="Verify uv is installed",
        )
        assert v.check_type == "command_exit_0"
        assert v.target == "uv --version"
        assert v.timeout_seconds == 10
        assert v.description == "Verify uv is installed"

    def test_construct_file_exists(self) -> None:
        v = ModelStepVerification(
            check_type="file_exists",
            target="/etc/hosts",
        )
        assert v.check_type == "file_exists"
        assert v.target == "/etc/hosts"
        assert v.description is None

    def test_construct_tcp_probe(self) -> None:
        v = ModelStepVerification(
            check_type="tcp_probe",
            target="localhost:5432",
            timeout_seconds=5,
        )
        assert v.check_type == "tcp_probe"
        assert v.timeout_seconds == 5

    def test_construct_http_health(self) -> None:
        v = ModelStepVerification(
            check_type="http_health",
            target="http://localhost:8080/health",
        )
        assert v.check_type == "http_health"

    def test_construct_python_import(self) -> None:
        v = ModelStepVerification(
            check_type="python_import",
            target="omnibase_core",
        )
        assert v.check_type == "python_import"

    def test_invalid_check_type_rejected(self) -> None:
        with pytest.raises(ValidationError):
            ModelStepVerification(
                check_type="invalid_type",  # type: ignore[arg-type]
                target="something",
            )

    def test_serialize_round_trip(self) -> None:
        v = ModelStepVerification(
            check_type="command_exit_0",
            target="python3 --version",
            timeout_seconds=15,
            description="Check Python 3",
        )
        data = v.model_dump()
        v2 = ModelStepVerification.model_validate(data)
        assert v == v2

    def test_json_round_trip(self) -> None:
        v = ModelStepVerification(
            check_type="tcp_probe",
            target="localhost:9092",
            timeout_seconds=3,
        )
        json_str = v.model_dump_json()
        v2 = ModelStepVerification.model_validate_json(json_str)
        assert v == v2

    def test_default_timeout(self) -> None:
        v = ModelStepVerification(
            check_type="file_exists",
            target="/tmp/test",
        )
        assert v.timeout_seconds == 10

    def test_custom_timeout(self) -> None:
        v = ModelStepVerification(
            check_type="http_health",
            target="http://localhost:8053/health",
            timeout_seconds=30,
        )
        assert v.timeout_seconds == 30

    def test_re_exported_from_orchestrator_init(self) -> None:
        """Verify ModelStepVerification is accessible from the orchestrator package."""
        from omnibase_core.models.orchestrator import ModelStepVerification as Imported

        assert Imported is ModelStepVerification
