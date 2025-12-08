"""Tests for ModelHealthCheck."""

import pytest
from pydantic import HttpUrl, ValidationError

from omnibase_core.enums.enum_health_check_type import EnumHealthCheckType
from omnibase_core.models.errors.model_onex_error import ModelOnexError
from omnibase_core.models.health.model_health_check import ModelHealthCheck


class TestModelHealthCheckBasics:
    """Test basic ModelHealthCheck functionality."""

    def test_http_get_initialization(self):
        """Test HTTP GET health check initialization."""
        check = ModelHealthCheck(
            check_type=EnumHealthCheckType.HTTP_GET,
            endpoint_path="/health",
            expected_status_code=200,
            timeout_seconds=5,
        )

        assert check.check_type == EnumHealthCheckType.HTTP_GET
        assert check.endpoint_path == "/health"
        assert check.expected_status_code == 200
        assert check.timeout_seconds == 5
        assert check.headers == {}

    def test_http_post_initialization(self):
        """Test HTTP POST health check initialization."""
        check = ModelHealthCheck(
            check_type=EnumHealthCheckType.HTTP_POST,
            endpoint_path="/health/check",
            expected_status_code=201,
            timeout_seconds=10,
        )

        assert check.check_type == EnumHealthCheckType.HTTP_POST
        assert check.endpoint_path == "/health/check"
        assert check.expected_status_code == 201
        assert check.timeout_seconds == 10

    def test_command_initialization(self):
        """Test command health check initialization."""
        check = ModelHealthCheck(
            check_type=EnumHealthCheckType.COMMAND,
            command="systemctl status myservice",
            timeout_seconds=3,
        )

        assert check.check_type == EnumHealthCheckType.COMMAND
        assert check.command == "systemctl status myservice"
        assert check.timeout_seconds == 3

    def test_initialization_with_full_url(self):
        """Test initialization with full URL."""
        check = ModelHealthCheck(
            check_type=EnumHealthCheckType.HTTP_GET,
            full_url=HttpUrl("https://example.com/health"),
            expected_status_code=200,
        )

        assert check.full_url == HttpUrl("https://example.com/health")
        assert check.endpoint_path is None

    def test_initialization_with_headers(self):
        """Test initialization with custom headers."""
        headers = {"Authorization": "Bearer token123", "X-Custom": "value"}
        check = ModelHealthCheck(
            check_type=EnumHealthCheckType.HTTP_GET,
            endpoint_path="/health",
            headers=headers,
        )

        assert check.headers == headers


class TestModelHealthCheckValidation:
    """Test ModelHealthCheck validation."""

    def test_endpoint_path_auto_prefix(self):
        """Test endpoint path gets auto-prefixed with /."""
        check = ModelHealthCheck(
            check_type=EnumHealthCheckType.HTTP_GET,
            endpoint_path="health",
        )

        assert check.endpoint_path == "/health"

    def test_endpoint_path_with_slash(self):
        """Test endpoint path already with / is unchanged."""
        check = ModelHealthCheck(
            check_type=EnumHealthCheckType.HTTP_GET,
            endpoint_path="/health",
        )

        assert check.endpoint_path == "/health"

    def test_command_required_for_command_type(self):
        """Test command is required when check_type is COMMAND."""
        with pytest.raises(ModelOnexError) as exc_info:
            ModelHealthCheck(
                check_type=EnumHealthCheckType.COMMAND,
                command=None,
            )

        assert "command is required when check_type is COMMAND" in str(exc_info.value)

    def test_command_optional_for_http_types(self):
        """Test command is optional for HTTP check types."""
        # Should not raise error
        ModelHealthCheck(
            check_type=EnumHealthCheckType.HTTP_GET,
            endpoint_path="/health",
            command=None,
        )

    def test_url_or_endpoint_required_for_http_get(self):
        """Test URL or endpoint required for HTTP GET."""
        with pytest.raises(ModelOnexError) as exc_info:
            ModelHealthCheck(
                check_type=EnumHealthCheckType.HTTP_GET,
                endpoint_path=None,
                full_url=None,
            )

        assert "Either full_url or endpoint_path required for HTTP checks" in str(
            exc_info.value
        )

    def test_url_or_endpoint_required_for_http_post(self):
        """Test URL or endpoint required for HTTP POST."""
        with pytest.raises(ModelOnexError) as exc_info:
            ModelHealthCheck(
                check_type=EnumHealthCheckType.HTTP_POST,
                endpoint_path=None,
                full_url=None,
            )

        assert "Either full_url or endpoint_path required for HTTP checks" in str(
            exc_info.value
        )

    def test_status_code_validation(self):
        """Test status code validation."""
        # Valid status codes
        ModelHealthCheck(
            check_type=EnumHealthCheckType.HTTP_GET,
            endpoint_path="/health",
            expected_status_code=100,
        )
        ModelHealthCheck(
            check_type=EnumHealthCheckType.HTTP_GET,
            endpoint_path="/health",
            expected_status_code=200,
        )
        ModelHealthCheck(
            check_type=EnumHealthCheckType.HTTP_GET,
            endpoint_path="/health",
            expected_status_code=599,
        )

        # Invalid status codes
        with pytest.raises(ValidationError):
            ModelHealthCheck(
                check_type=EnumHealthCheckType.HTTP_GET,
                endpoint_path="/health",
                expected_status_code=99,
            )
        with pytest.raises(ValidationError):
            ModelHealthCheck(
                check_type=EnumHealthCheckType.HTTP_GET,
                endpoint_path="/health",
                expected_status_code=600,
            )

    def test_timeout_validation(self):
        """Test timeout validation."""
        # Valid timeouts
        ModelHealthCheck(
            check_type=EnumHealthCheckType.HTTP_GET,
            endpoint_path="/health",
            timeout_seconds=1,
        )
        ModelHealthCheck(
            check_type=EnumHealthCheckType.HTTP_GET,
            endpoint_path="/health",
            timeout_seconds=300,
        )

        # Invalid timeouts
        with pytest.raises(ValidationError):
            ModelHealthCheck(
                check_type=EnumHealthCheckType.HTTP_GET,
                endpoint_path="/health",
                timeout_seconds=0,
            )
        with pytest.raises(ValidationError):
            ModelHealthCheck(
                check_type=EnumHealthCheckType.HTTP_GET,
                endpoint_path="/health",
                timeout_seconds=301,
            )


class TestModelHealthCheckURLGeneration:
    """Test URL generation methods."""

    def test_get_effective_url_with_full_url(self):
        """Test get_effective_url with full_url set."""
        check = ModelHealthCheck(
            check_type=EnumHealthCheckType.HTTP_GET,
            full_url=HttpUrl("https://example.com/health"),
        )

        url = check.get_effective_url()
        assert url == "https://example.com/health"

    def test_get_effective_url_with_endpoint_and_base(self):
        """Test get_effective_url with endpoint_path and base_url."""
        check = ModelHealthCheck(
            check_type=EnumHealthCheckType.HTTP_GET,
            endpoint_path="/health",
        )

        url = check.get_effective_url("https://api.example.com")
        assert url == "https://api.example.com/health"

    def test_get_effective_url_with_trailing_slash(self):
        """Test get_effective_url handles trailing slash."""
        check = ModelHealthCheck(
            check_type=EnumHealthCheckType.HTTP_GET,
            endpoint_path="/health",
        )

        url = check.get_effective_url("https://api.example.com/")
        assert url == "https://api.example.com/health"

    def test_get_effective_url_endpoint_only(self):
        """Test get_effective_url with endpoint_path only."""
        check = ModelHealthCheck(
            check_type=EnumHealthCheckType.HTTP_GET,
            endpoint_path="/health",
        )

        url = check.get_effective_url()
        assert url == "/health"

    def test_get_effective_url_no_url(self):
        """Test get_effective_url with no URL set."""
        check = ModelHealthCheck(
            check_type=EnumHealthCheckType.COMMAND,
            command="test",
        )

        url = check.get_effective_url()
        assert url == ""


class TestModelHealthCheckTypeChecking:
    """Test type checking methods."""

    def test_is_http_check_http_get(self):
        """Test is_http_check for HTTP GET."""
        check = ModelHealthCheck(
            check_type=EnumHealthCheckType.HTTP_GET,
            endpoint_path="/health",
        )

        assert check.is_http_check() is True

    def test_is_http_check_http_post(self):
        """Test is_http_check for HTTP POST."""
        check = ModelHealthCheck(
            check_type=EnumHealthCheckType.HTTP_POST,
            endpoint_path="/health",
        )

        assert check.is_http_check() is True

    def test_is_http_check_command(self):
        """Test is_http_check for COMMAND type."""
        check = ModelHealthCheck(
            check_type=EnumHealthCheckType.COMMAND,
            command="test",
        )

        assert check.is_http_check() is False


class TestModelHealthCheckTimeout:
    """Test timeout methods."""

    def test_get_effective_timeout_default(self):
        """Test get_effective_timeout returns configured value."""
        check = ModelHealthCheck(
            check_type=EnumHealthCheckType.HTTP_GET,
            endpoint_path="/health",
            timeout_seconds=10,
        )

        assert check.get_effective_timeout() == 10

    def test_get_effective_timeout_custom(self):
        """Test get_effective_timeout with custom value."""
        check = ModelHealthCheck(
            check_type=EnumHealthCheckType.HTTP_GET,
            endpoint_path="/health",
            timeout_seconds=30,
        )

        assert check.get_effective_timeout() == 30


class TestModelHealthCheckConfiguration:
    """Test health check configuration."""

    def test_expected_response_pattern(self):
        """Test expected response pattern configuration."""
        check = ModelHealthCheck(
            check_type=EnumHealthCheckType.HTTP_GET,
            endpoint_path="/health",
            expected_response_pattern=r"status.*ok",
        )

        assert check.expected_response_pattern == r"status.*ok"

    def test_custom_headers(self):
        """Test custom headers configuration."""
        headers = {
            "Authorization": "Bearer token",
            "X-Custom-Header": "value",
            "Accept": "application/json",
        }
        check = ModelHealthCheck(
            check_type=EnumHealthCheckType.HTTP_GET,
            endpoint_path="/health",
            headers=headers,
        )

        assert check.headers == headers
        assert len(check.headers) == 3

    def test_metadata_configuration(self):
        """Test metadata configuration."""
        from omnibase_core.models.core.model_protocol_metadata import (
            ModelGenericMetadata,
        )
        from omnibase_core.models.primitives.model_semver import ModelSemVer

        metadata = ModelGenericMetadata(version=ModelSemVer(major=1, minor=0, patch=0))
        check = ModelHealthCheck(
            check_type=EnumHealthCheckType.HTTP_GET,
            endpoint_path="/health",
            metadata=metadata,
        )

        assert check.metadata == metadata


class TestModelHealthCheckEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_empty_endpoint_path_with_full_url(self):
        """Test empty endpoint_path when full_url is provided."""
        check = ModelHealthCheck(
            check_type=EnumHealthCheckType.HTTP_GET,
            full_url=HttpUrl("https://example.com/health"),
            endpoint_path=None,
        )

        assert check.full_url is not None
        assert check.endpoint_path is None

    def test_both_endpoint_and_full_url(self):
        """Test providing both endpoint_path and full_url."""
        check = ModelHealthCheck(
            check_type=EnumHealthCheckType.HTTP_GET,
            endpoint_path="/health",
            full_url=HttpUrl("https://example.com/health"),
        )

        # full_url should take precedence
        url = check.get_effective_url()
        assert url == "https://example.com/health"

    def test_minimum_timeout(self):
        """Test minimum timeout value."""
        check = ModelHealthCheck(
            check_type=EnumHealthCheckType.HTTP_GET,
            endpoint_path="/health",
            timeout_seconds=1,
        )

        assert check.timeout_seconds == 1

    def test_maximum_timeout(self):
        """Test maximum timeout value."""
        check = ModelHealthCheck(
            check_type=EnumHealthCheckType.HTTP_GET,
            endpoint_path="/health",
            timeout_seconds=300,
        )

        assert check.timeout_seconds == 300

    def test_default_timeout(self):
        """Test default timeout value."""
        check = ModelHealthCheck(
            check_type=EnumHealthCheckType.HTTP_GET,
            endpoint_path="/health",
        )

        assert check.timeout_seconds == 5

    def test_default_expected_status_code(self):
        """Test default expected status code."""
        check = ModelHealthCheck(
            check_type=EnumHealthCheckType.HTTP_GET,
            endpoint_path="/health",
        )

        assert check.expected_status_code == 200

    def test_complex_url_construction(self):
        """Test complex URL construction scenarios."""
        check = ModelHealthCheck(
            check_type=EnumHealthCheckType.HTTP_GET,
            endpoint_path="/api/v1/health/status",
        )

        # With base URL
        url = check.get_effective_url("https://api.example.com:8080")
        assert url == "https://api.example.com:8080/api/v1/health/status"

        # With trailing slashes
        url = check.get_effective_url("https://api.example.com:8080/")
        assert url == "https://api.example.com:8080/api/v1/health/status"


class TestModelHealthCheckCommandType:
    """Test command-specific functionality."""

    def test_command_check_with_valid_command(self):
        """Test command check with valid command."""
        check = ModelHealthCheck(
            check_type=EnumHealthCheckType.COMMAND,
            command="systemctl status myservice",
            timeout_seconds=5,
        )

        assert check.command == "systemctl status myservice"
        assert check.is_http_check() is False
        assert check.timeout_seconds == 5

    def test_command_check_complex_command(self):
        """Test command check with complex command."""
        complex_cmd = "docker ps | grep mycontainer | wc -l"
        check = ModelHealthCheck(
            check_type=EnumHealthCheckType.COMMAND,
            command=complex_cmd,
        )

        assert check.command == complex_cmd

    def test_command_check_with_expected_pattern(self):
        """Test command check with expected response pattern."""
        check = ModelHealthCheck(
            check_type=EnumHealthCheckType.COMMAND,
            command="echo 'status: ok'",
            expected_response_pattern=r"status:\s*ok",
        )

        assert check.expected_response_pattern == r"status:\s*ok"
