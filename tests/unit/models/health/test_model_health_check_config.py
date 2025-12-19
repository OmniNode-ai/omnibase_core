"""Tests for ModelHealthCheckConfig."""

import pytest

from omnibase_core.models.health.model_health_check_config import ModelHealthCheckConfig


@pytest.mark.unit
class TestModelHealthCheckConfigBasics:
    """Test basic functionality."""

    def test_default_initialization(self):
        """Test default config initialization."""
        config = ModelHealthCheckConfig()

        assert config.enabled is True
        assert config.check_interval_seconds == 30
        assert config.timeout_seconds == 5
        assert config.healthy_threshold == 3
        assert config.unhealthy_threshold == 2
        assert config.check_path == "/health"
        assert config.check_method == "GET"
        assert config.expected_status_codes == [200]
        assert config.validate_ssl is True

    def test_custom_initialization(self):
        """Test custom config initialization."""
        config = ModelHealthCheckConfig(
            enabled=False,
            check_interval_seconds=60,
            timeout_seconds=10,
            healthy_threshold=5,
            unhealthy_threshold=3,
            check_path="/api/health",
            check_method="POST",
            expected_status_codes=[200, 201],
        )

        assert config.enabled is False
        assert config.check_interval_seconds == 60
        assert config.timeout_seconds == 10
        assert config.healthy_threshold == 5
        assert config.unhealthy_threshold == 3
        assert config.check_path == "/api/health"
        assert config.check_method == "POST"
        assert config.expected_status_codes == [200, 201]


@pytest.mark.unit
class TestModelHealthCheckConfigValidation:
    """Test validation."""

    def test_interval_validation(self):
        """Test check interval validation."""
        # Valid intervals
        ModelHealthCheckConfig(check_interval_seconds=5)
        ModelHealthCheckConfig(check_interval_seconds=3600)

        # Invalid intervals
        with pytest.raises(Exception):
            ModelHealthCheckConfig(check_interval_seconds=4)
        with pytest.raises(Exception):
            ModelHealthCheckConfig(check_interval_seconds=3601)

    def test_timeout_validation(self):
        """Test timeout validation."""
        # Valid timeouts
        ModelHealthCheckConfig(timeout_seconds=1)
        ModelHealthCheckConfig(timeout_seconds=60)

        # Invalid timeouts
        with pytest.raises(Exception):
            ModelHealthCheckConfig(timeout_seconds=0)
        with pytest.raises(Exception):
            ModelHealthCheckConfig(timeout_seconds=61)

    def test_threshold_validation(self):
        """Test threshold validation."""
        # Valid thresholds
        ModelHealthCheckConfig(healthy_threshold=1, unhealthy_threshold=1)
        ModelHealthCheckConfig(healthy_threshold=10, unhealthy_threshold=10)

        # Invalid thresholds
        with pytest.raises(Exception):
            ModelHealthCheckConfig(healthy_threshold=0)
        with pytest.raises(Exception):
            ModelHealthCheckConfig(unhealthy_threshold=11)

    def test_method_validation(self):
        """Test HTTP method validation."""
        # Valid methods
        ModelHealthCheckConfig(check_method="GET")
        ModelHealthCheckConfig(check_method="POST")
        ModelHealthCheckConfig(check_method="HEAD")
        ModelHealthCheckConfig(check_method="OPTIONS")

        # Invalid method
        with pytest.raises(Exception):
            ModelHealthCheckConfig(check_method="INVALID")


@pytest.mark.unit
class TestModelHealthCheckConfigResponseValidation:
    """Test response validation."""

    def test_is_response_healthy_disabled(self):
        """Test response validation when disabled."""
        config = ModelHealthCheckConfig(enabled=False)

        assert config.is_response_healthy(404, "error") is True

    def test_is_response_healthy_status_code(self):
        """Test response validation by status code."""
        config = ModelHealthCheckConfig(expected_status_codes=[200, 201])

        assert config.is_response_healthy(200, "") is True
        assert config.is_response_healthy(201, "") is True
        assert config.is_response_healthy(404, "") is False

    def test_is_response_healthy_with_body(self):
        """Test response validation with expected body."""
        config = ModelHealthCheckConfig(expected_response_body="ok")

        assert config.is_response_healthy(200, "status: ok") is True
        assert config.is_response_healthy(200, "status: error") is False

    def test_is_response_healthy_both_checks(self):
        """Test response validation with status and body."""
        config = ModelHealthCheckConfig(
            expected_status_codes=[200], expected_response_body="ok"
        )

        assert config.is_response_healthy(200, "status: ok") is True
        assert config.is_response_healthy(201, "status: ok") is False
        assert config.is_response_healthy(200, "error") is False


@pytest.mark.unit
class TestModelHealthCheckConfigURLGeneration:
    """Test URL generation."""

    def test_get_check_url(self):
        """Test check URL generation."""
        config = ModelHealthCheckConfig(check_path="/health")

        url = config.get_check_url("https://api.example.com")
        assert url == "https://api.example.com/health"

    def test_get_check_url_trailing_slash(self):
        """Test URL generation with trailing slash."""
        config = ModelHealthCheckConfig(check_path="/health")

        url = config.get_check_url("https://api.example.com/")
        assert url == "https://api.example.com/health"

    def test_get_check_url_leading_slash(self):
        """Test URL generation with leading slash in path."""
        config = ModelHealthCheckConfig(check_path="health")

        url = config.get_check_url("https://api.example.com")
        assert url == "https://api.example.com/health"


@pytest.mark.unit
class TestModelHealthCheckConfigHeaders:
    """Test header management."""

    def test_get_check_headers_with_defaults(self):
        """Test headers with defaults."""
        config = ModelHealthCheckConfig()

        headers = config.get_check_headers_with_defaults()
        assert "User-Agent" in headers
        assert "Accept" in headers
        assert headers["User-Agent"] == "ONEX-LoadBalancer/1.0"

    def test_get_check_headers_custom(self):
        """Test headers with custom values."""
        config = ModelHealthCheckConfig(check_headers={"Authorization": "Bearer token"})

        headers = config.get_check_headers_with_defaults()
        assert headers["Authorization"] == "Bearer token"
        assert "User-Agent" in headers


@pytest.mark.unit
class TestModelHealthCheckConfigTiming:
    """Test timing methods."""

    def test_should_check_now_enabled(self):
        """Test should_check_now when enabled."""
        config = ModelHealthCheckConfig(check_interval_seconds=30)

        assert config.should_check_now(0, 30) is True
        assert config.should_check_now(0, 60) is True
        assert config.should_check_now(0, 29) is False

    def test_should_check_now_disabled(self):
        """Test should_check_now when disabled."""
        config = ModelHealthCheckConfig(enabled=False)

        assert config.should_check_now(0, 100) is False


@pytest.mark.unit
class TestModelHealthCheckConfigHealthStatus:
    """Test health status calculation."""

    def test_calculate_health_status_unhealthy(self):
        """Test health status calculation for unhealthy."""
        config = ModelHealthCheckConfig(unhealthy_threshold=2)

        status = config.calculate_health_status(0, 2)
        assert status == "unhealthy"

    def test_calculate_health_status_healthy(self):
        """Test health status calculation for healthy."""
        config = ModelHealthCheckConfig(healthy_threshold=3)

        status = config.calculate_health_status(3, 0)
        assert status == "healthy"

    def test_calculate_health_status_degraded(self):
        """Test health status calculation for degraded."""
        config = ModelHealthCheckConfig(healthy_threshold=3, unhealthy_threshold=2)

        status = config.calculate_health_status(1, 1)
        assert status == "degraded"


@pytest.mark.unit
class TestModelHealthCheckConfigTimeout:
    """Test timeout methods."""

    def test_get_effective_timeout_normal(self):
        """Test effective timeout normal case."""
        config = ModelHealthCheckConfig(timeout_seconds=5, check_interval_seconds=30)

        assert config.get_effective_timeout() == 5

    def test_get_effective_timeout_exceeds_interval(self):
        """Test effective timeout when exceeding interval."""
        config = ModelHealthCheckConfig(timeout_seconds=20, check_interval_seconds=30)

        # Should be capped at half the interval
        assert config.get_effective_timeout() == 15


@pytest.mark.unit
class TestModelHealthCheckConfigFactoryMethods:
    """Test factory methods."""

    def test_create_fast_checks(self):
        """Test fast checks factory."""
        config = ModelHealthCheckConfig.create_fast_checks()

        assert config.enabled is True
        assert config.check_interval_seconds == 10
        assert config.timeout_seconds == 2
        assert config.healthy_threshold == 2
        assert config.unhealthy_threshold == 2
        assert config.check_method == "HEAD"

    def test_create_thorough_checks(self):
        """Test thorough checks factory."""
        config = ModelHealthCheckConfig.create_thorough_checks()

        assert config.enabled is True
        assert config.check_interval_seconds == 60
        assert config.timeout_seconds == 10
        assert config.healthy_threshold == 3
        assert config.unhealthy_threshold == 3
        assert config.check_path == "/health/detailed"
        assert config.expected_response_body == "healthy"

    def test_create_production_checks(self):
        """Test production checks factory."""
        config = ModelHealthCheckConfig.create_production_checks()

        assert config.enabled is True
        assert config.check_interval_seconds == 30
        assert config.validate_ssl is True
        assert "X-Environment" in config.check_headers
        assert config.check_headers["X-Environment"] == "production"

    def test_create_development_checks(self):
        """Test development checks factory."""
        config = ModelHealthCheckConfig.create_development_checks()

        assert config.enabled is True
        assert config.validate_ssl is False
        assert "X-Environment" in config.check_headers
        assert config.check_headers["X-Environment"] == "development"

    def test_create_disabled(self):
        """Test disabled checks factory."""
        config = ModelHealthCheckConfig.create_disabled()

        assert config.enabled is False
