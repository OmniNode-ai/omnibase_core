"""
Unit tests for constants_timeouts module.

Tests the centralized timeout constants for the ONEX framework.

VERSION: 1.0.0
"""

import pytest

# Module-level pytest marker for all tests in this file
pytestmark = pytest.mark.unit


@pytest.mark.unit
class TestTimeoutConstantValues:
    """Tests for the expected values of timeout constants."""

    def test_timeout_default_ms_value(self) -> None:
        """TIMEOUT_DEFAULT_MS should be 30000ms (30 seconds)."""
        from omnibase_core.constants.constants_timeouts import TIMEOUT_DEFAULT_MS

        assert TIMEOUT_DEFAULT_MS == 30000

    def test_timeout_long_ms_value(self) -> None:
        """TIMEOUT_LONG_MS should be 300000ms (5 minutes)."""
        from omnibase_core.constants.constants_timeouts import TIMEOUT_LONG_MS

        assert TIMEOUT_LONG_MS == 300000

    def test_timeout_min_ms_value(self) -> None:
        """TIMEOUT_MIN_MS should be 1000ms (1 second)."""
        from omnibase_core.constants.constants_timeouts import TIMEOUT_MIN_MS

        assert TIMEOUT_MIN_MS == 1000

    def test_timeout_max_ms_value(self) -> None:
        """TIMEOUT_MAX_MS should be 600000ms (10 minutes)."""
        from omnibase_core.constants.constants_timeouts import TIMEOUT_MAX_MS

        assert TIMEOUT_MAX_MS == 600000


@pytest.mark.unit
class TestTimeoutConstantTypes:
    """Tests for type validation of timeout constants."""

    def test_timeout_default_ms_is_int(self) -> None:
        """TIMEOUT_DEFAULT_MS should be an integer."""
        from omnibase_core.constants.constants_timeouts import TIMEOUT_DEFAULT_MS

        assert isinstance(TIMEOUT_DEFAULT_MS, int)

    def test_timeout_long_ms_is_int(self) -> None:
        """TIMEOUT_LONG_MS should be an integer."""
        from omnibase_core.constants.constants_timeouts import TIMEOUT_LONG_MS

        assert isinstance(TIMEOUT_LONG_MS, int)

    def test_timeout_min_ms_is_int(self) -> None:
        """TIMEOUT_MIN_MS should be an integer."""
        from omnibase_core.constants.constants_timeouts import TIMEOUT_MIN_MS

        assert isinstance(TIMEOUT_MIN_MS, int)

    def test_timeout_max_ms_is_int(self) -> None:
        """TIMEOUT_MAX_MS should be an integer."""
        from omnibase_core.constants.constants_timeouts import TIMEOUT_MAX_MS

        assert isinstance(TIMEOUT_MAX_MS, int)


@pytest.mark.unit
class TestTimeoutConstantOrdering:
    """Tests for logical ordering of timeout constants."""

    def test_min_less_than_default(self) -> None:
        """TIMEOUT_MIN_MS should be less than TIMEOUT_DEFAULT_MS."""
        from omnibase_core.constants.constants_timeouts import (
            TIMEOUT_DEFAULT_MS,
            TIMEOUT_MIN_MS,
        )

        assert TIMEOUT_MIN_MS < TIMEOUT_DEFAULT_MS

    def test_default_less_than_long(self) -> None:
        """TIMEOUT_DEFAULT_MS should be less than TIMEOUT_LONG_MS."""
        from omnibase_core.constants.constants_timeouts import (
            TIMEOUT_DEFAULT_MS,
            TIMEOUT_LONG_MS,
        )

        assert TIMEOUT_DEFAULT_MS < TIMEOUT_LONG_MS

    def test_long_less_than_max(self) -> None:
        """TIMEOUT_LONG_MS should be less than TIMEOUT_MAX_MS."""
        from omnibase_core.constants.constants_timeouts import (
            TIMEOUT_LONG_MS,
            TIMEOUT_MAX_MS,
        )

        assert TIMEOUT_LONG_MS < TIMEOUT_MAX_MS

    def test_full_ordering(self) -> None:
        """All timeout constants should follow: MIN < DEFAULT < LONG < MAX."""
        from omnibase_core.constants.constants_timeouts import (
            TIMEOUT_DEFAULT_MS,
            TIMEOUT_LONG_MS,
            TIMEOUT_MAX_MS,
            TIMEOUT_MIN_MS,
        )

        assert TIMEOUT_MIN_MS < TIMEOUT_DEFAULT_MS < TIMEOUT_LONG_MS < TIMEOUT_MAX_MS

    def test_all_constants_are_positive(self) -> None:
        """All timeout constants should be positive values."""
        from omnibase_core.constants.constants_timeouts import (
            TIMEOUT_DEFAULT_MS,
            TIMEOUT_LONG_MS,
            TIMEOUT_MAX_MS,
            TIMEOUT_MIN_MS,
        )

        assert TIMEOUT_MIN_MS > 0
        assert TIMEOUT_DEFAULT_MS > 0
        assert TIMEOUT_LONG_MS > 0
        assert TIMEOUT_MAX_MS > 0


@pytest.mark.unit
class TestTimeoutConstantPublicAPI:
    """Tests for public API exports from omnibase_core.constants."""

    def test_timeout_default_ms_exported_from_public_api(self) -> None:
        """TIMEOUT_DEFAULT_MS should be exported from omnibase_core.constants."""
        from omnibase_core.constants import TIMEOUT_DEFAULT_MS

        assert TIMEOUT_DEFAULT_MS == 30000

    def test_timeout_long_ms_exported_from_public_api(self) -> None:
        """TIMEOUT_LONG_MS should be exported from omnibase_core.constants."""
        from omnibase_core.constants import TIMEOUT_LONG_MS

        assert TIMEOUT_LONG_MS == 300000

    def test_timeout_min_ms_exported_from_public_api(self) -> None:
        """TIMEOUT_MIN_MS should be exported from omnibase_core.constants."""
        from omnibase_core.constants import TIMEOUT_MIN_MS

        assert TIMEOUT_MIN_MS == 1000

    def test_timeout_max_ms_exported_from_public_api(self) -> None:
        """TIMEOUT_MAX_MS should be exported from omnibase_core.constants."""
        from omnibase_core.constants import TIMEOUT_MAX_MS

        assert TIMEOUT_MAX_MS == 600000

    def test_all_timeout_constants_in_public_api_all(self) -> None:
        """All timeout constants should be listed in __all__."""
        from omnibase_core.constants import __all__

        expected_constants = [
            "TIMEOUT_DEFAULT_MS",
            "TIMEOUT_LONG_MS",
            "TIMEOUT_MIN_MS",
            "TIMEOUT_MAX_MS",
            "THREAD_JOIN_TIMEOUT_SECONDS",
            "PROCESS_SHUTDOWN_TIMEOUT_SECONDS",
            "HTTP_REQUEST_TIMEOUT_SECONDS",
            "KAFKA_REQUEST_TIMEOUT_MS",
            "DEFAULT_CACHE_TTL_SECONDS",
        ]
        for const in expected_constants:
            assert const in __all__, f"{const} should be in __all__"

    def test_thread_join_timeout_exported_from_public_api(self) -> None:
        """THREAD_JOIN_TIMEOUT_SECONDS should be exported from omnibase_core.constants."""
        from omnibase_core.constants import THREAD_JOIN_TIMEOUT_SECONDS

        assert THREAD_JOIN_TIMEOUT_SECONDS == 5.0

    def test_process_shutdown_timeout_exported_from_public_api(self) -> None:
        """PROCESS_SHUTDOWN_TIMEOUT_SECONDS should be exported from omnibase_core.constants."""
        from omnibase_core.constants import PROCESS_SHUTDOWN_TIMEOUT_SECONDS

        assert PROCESS_SHUTDOWN_TIMEOUT_SECONDS == 10.0

    def test_http_request_timeout_exported_from_public_api(self) -> None:
        """HTTP_REQUEST_TIMEOUT_SECONDS should be exported from omnibase_core.constants."""
        from omnibase_core.constants import HTTP_REQUEST_TIMEOUT_SECONDS

        assert HTTP_REQUEST_TIMEOUT_SECONDS == 30.0

    def test_kafka_request_timeout_exported_from_public_api(self) -> None:
        """KAFKA_REQUEST_TIMEOUT_MS should be exported from omnibase_core.constants."""
        from omnibase_core.constants import KAFKA_REQUEST_TIMEOUT_MS

        assert KAFKA_REQUEST_TIMEOUT_MS == 5000

    def test_default_cache_ttl_exported_from_public_api(self) -> None:
        """DEFAULT_CACHE_TTL_SECONDS should be exported from omnibase_core.constants."""
        from omnibase_core.constants import DEFAULT_CACHE_TTL_SECONDS

        assert DEFAULT_CACHE_TTL_SECONDS == 300


@pytest.mark.unit
class TestTimeoutConstantModuleExports:
    """Tests for module-level __all__ exports."""

    def test_constants_timeouts_all_exports(self) -> None:
        """All expected constants should be in constants_timeouts.__all__."""
        from omnibase_core.constants.constants_timeouts import __all__

        expected_exports = [
            "TIMEOUT_DEFAULT_MS",
            "TIMEOUT_LONG_MS",
            "TIMEOUT_MIN_MS",
            "TIMEOUT_MAX_MS",
            "THREAD_JOIN_TIMEOUT_SECONDS",
            "PROCESS_SHUTDOWN_TIMEOUT_SECONDS",
            "HTTP_REQUEST_TIMEOUT_SECONDS",
            "KAFKA_REQUEST_TIMEOUT_MS",
            "DEFAULT_CACHE_TTL_SECONDS",
        ]
        for export in expected_exports:
            assert export in __all__, f"{export} should be in __all__"

    def test_constants_timeouts_all_length(self) -> None:
        """__all__ should contain exactly 9 exports."""
        from omnibase_core.constants.constants_timeouts import __all__

        assert len(__all__) == 9


@pytest.mark.unit
class TestBackwardsCompatibilityAliases:
    """Tests for backwards compatibility with legacy timeout constants."""

    def test_default_operation_timeout_ms_equals_timeout_default_ms(self) -> None:
        """DEFAULT_OPERATION_TIMEOUT_MS should equal TIMEOUT_DEFAULT_MS.

        This ensures backwards compatibility for code using the legacy
        DEFAULT_OPERATION_TIMEOUT_MS constant from constants_effect.py.
        """
        from omnibase_core.constants.constants_effect import (
            DEFAULT_OPERATION_TIMEOUT_MS,
        )
        from omnibase_core.constants.constants_timeouts import TIMEOUT_DEFAULT_MS

        assert DEFAULT_OPERATION_TIMEOUT_MS == TIMEOUT_DEFAULT_MS

    def test_effect_timeout_default_ms_equals_timeout_default_ms(self) -> None:
        """EFFECT_TIMEOUT_DEFAULT_MS should equal TIMEOUT_DEFAULT_MS.

        This ensures backwards compatibility for code using the legacy
        EFFECT_TIMEOUT_DEFAULT_MS constant from constants_effect_limits.py.
        """
        from omnibase_core.constants.constants_effect_limits import (
            EFFECT_TIMEOUT_DEFAULT_MS,
        )
        from omnibase_core.constants.constants_timeouts import TIMEOUT_DEFAULT_MS

        assert EFFECT_TIMEOUT_DEFAULT_MS == TIMEOUT_DEFAULT_MS

    def test_effect_timeout_min_ms_equals_timeout_min_ms(self) -> None:
        """EFFECT_TIMEOUT_MIN_MS should equal TIMEOUT_MIN_MS.

        Both constants represent the minimum timeout bound (1 second).
        """
        from omnibase_core.constants.constants_effect_limits import (
            EFFECT_TIMEOUT_MIN_MS,
        )
        from omnibase_core.constants.constants_timeouts import TIMEOUT_MIN_MS

        assert EFFECT_TIMEOUT_MIN_MS == TIMEOUT_MIN_MS

    def test_effect_timeout_max_ms_equals_timeout_max_ms(self) -> None:
        """EFFECT_TIMEOUT_MAX_MS should equal TIMEOUT_MAX_MS.

        Both constants represent the maximum timeout bound (10 minutes).
        """
        from omnibase_core.constants.constants_effect_limits import (
            EFFECT_TIMEOUT_MAX_MS,
        )
        from omnibase_core.constants.constants_timeouts import TIMEOUT_MAX_MS

        assert EFFECT_TIMEOUT_MAX_MS == TIMEOUT_MAX_MS


@pytest.mark.unit
class TestTimeoutConstantSemantics:
    """Tests for semantic correctness of timeout constant definitions."""

    def test_timeout_min_is_one_second(self) -> None:
        """TIMEOUT_MIN_MS should represent 1 second in milliseconds."""
        from omnibase_core.constants.constants_timeouts import TIMEOUT_MIN_MS

        one_second_in_ms = 1 * 1000
        assert one_second_in_ms == TIMEOUT_MIN_MS

    def test_timeout_default_is_thirty_seconds(self) -> None:
        """TIMEOUT_DEFAULT_MS should represent 30 seconds in milliseconds."""
        from omnibase_core.constants.constants_timeouts import TIMEOUT_DEFAULT_MS

        thirty_seconds_in_ms = 30 * 1000
        assert thirty_seconds_in_ms == TIMEOUT_DEFAULT_MS

    def test_timeout_long_is_five_minutes(self) -> None:
        """TIMEOUT_LONG_MS should represent 5 minutes in milliseconds."""
        from omnibase_core.constants.constants_timeouts import TIMEOUT_LONG_MS

        five_minutes_in_ms = 5 * 60 * 1000
        assert five_minutes_in_ms == TIMEOUT_LONG_MS

    def test_timeout_max_is_ten_minutes(self) -> None:
        """TIMEOUT_MAX_MS should represent 10 minutes in milliseconds."""
        from omnibase_core.constants.constants_timeouts import TIMEOUT_MAX_MS

        ten_minutes_in_ms = 10 * 60 * 1000
        assert ten_minutes_in_ms == TIMEOUT_MAX_MS


@pytest.mark.unit
class TestThreadProcessTimeoutValues:
    """Tests for the expected values of thread/process timeout constants."""

    def test_thread_join_timeout_seconds_value(self) -> None:
        """THREAD_JOIN_TIMEOUT_SECONDS should be 5.0 seconds."""
        from omnibase_core.constants.constants_timeouts import (
            THREAD_JOIN_TIMEOUT_SECONDS,
        )

        assert THREAD_JOIN_TIMEOUT_SECONDS == 5.0

    def test_process_shutdown_timeout_seconds_value(self) -> None:
        """PROCESS_SHUTDOWN_TIMEOUT_SECONDS should be 10.0 seconds."""
        from omnibase_core.constants.constants_timeouts import (
            PROCESS_SHUTDOWN_TIMEOUT_SECONDS,
        )

        assert PROCESS_SHUTDOWN_TIMEOUT_SECONDS == 10.0

    def test_thread_join_is_positive(self) -> None:
        """THREAD_JOIN_TIMEOUT_SECONDS should be a positive value."""
        from omnibase_core.constants.constants_timeouts import (
            THREAD_JOIN_TIMEOUT_SECONDS,
        )

        assert THREAD_JOIN_TIMEOUT_SECONDS > 0

    def test_process_shutdown_is_positive(self) -> None:
        """PROCESS_SHUTDOWN_TIMEOUT_SECONDS should be a positive value."""
        from omnibase_core.constants.constants_timeouts import (
            PROCESS_SHUTDOWN_TIMEOUT_SECONDS,
        )

        assert PROCESS_SHUTDOWN_TIMEOUT_SECONDS > 0

    def test_process_shutdown_greater_than_thread_join(self) -> None:
        """PROCESS_SHUTDOWN_TIMEOUT_SECONDS should be greater than THREAD_JOIN_TIMEOUT_SECONDS."""
        from omnibase_core.constants.constants_timeouts import (
            PROCESS_SHUTDOWN_TIMEOUT_SECONDS,
            THREAD_JOIN_TIMEOUT_SECONDS,
        )

        assert PROCESS_SHUTDOWN_TIMEOUT_SECONDS > THREAD_JOIN_TIMEOUT_SECONDS


@pytest.mark.unit
class TestThreadProcessTimeoutTypes:
    """Tests for type validation of thread/process timeout constants."""

    def test_thread_join_timeout_seconds_is_float(self) -> None:
        """THREAD_JOIN_TIMEOUT_SECONDS should be a float."""
        from omnibase_core.constants.constants_timeouts import (
            THREAD_JOIN_TIMEOUT_SECONDS,
        )

        assert isinstance(THREAD_JOIN_TIMEOUT_SECONDS, float)

    def test_process_shutdown_timeout_seconds_is_float(self) -> None:
        """PROCESS_SHUTDOWN_TIMEOUT_SECONDS should be a float."""
        from omnibase_core.constants.constants_timeouts import (
            PROCESS_SHUTDOWN_TIMEOUT_SECONDS,
        )

        assert isinstance(PROCESS_SHUTDOWN_TIMEOUT_SECONDS, float)


@pytest.mark.unit
class TestNetworkTimeoutValues:
    """Tests for the expected values of network timeout constants."""

    def test_http_request_timeout_seconds_value(self) -> None:
        """HTTP_REQUEST_TIMEOUT_SECONDS should be 30.0 seconds."""
        from omnibase_core.constants.constants_timeouts import (
            HTTP_REQUEST_TIMEOUT_SECONDS,
        )

        assert HTTP_REQUEST_TIMEOUT_SECONDS == 30.0

    def test_kafka_request_timeout_ms_value(self) -> None:
        """KAFKA_REQUEST_TIMEOUT_MS should be 5000ms (5 seconds)."""
        from omnibase_core.constants.constants_timeouts import KAFKA_REQUEST_TIMEOUT_MS

        assert KAFKA_REQUEST_TIMEOUT_MS == 5000

    def test_http_request_timeout_is_positive(self) -> None:
        """HTTP_REQUEST_TIMEOUT_SECONDS should be a positive value."""
        from omnibase_core.constants.constants_timeouts import (
            HTTP_REQUEST_TIMEOUT_SECONDS,
        )

        assert HTTP_REQUEST_TIMEOUT_SECONDS > 0

    def test_kafka_request_timeout_is_positive(self) -> None:
        """KAFKA_REQUEST_TIMEOUT_MS should be a positive value."""
        from omnibase_core.constants.constants_timeouts import KAFKA_REQUEST_TIMEOUT_MS

        assert KAFKA_REQUEST_TIMEOUT_MS > 0

    def test_http_timeout_matches_default_ms_in_seconds(self) -> None:
        """HTTP_REQUEST_TIMEOUT_SECONDS should match TIMEOUT_DEFAULT_MS converted to seconds."""
        from omnibase_core.constants.constants_timeouts import (
            HTTP_REQUEST_TIMEOUT_SECONDS,
            TIMEOUT_DEFAULT_MS,
        )

        assert HTTP_REQUEST_TIMEOUT_SECONDS == TIMEOUT_DEFAULT_MS / 1000


@pytest.mark.unit
class TestNetworkTimeoutTypes:
    """Tests for type validation of network timeout constants."""

    def test_http_request_timeout_seconds_is_float(self) -> None:
        """HTTP_REQUEST_TIMEOUT_SECONDS should be a float."""
        from omnibase_core.constants.constants_timeouts import (
            HTTP_REQUEST_TIMEOUT_SECONDS,
        )

        assert isinstance(HTTP_REQUEST_TIMEOUT_SECONDS, float)

    def test_kafka_request_timeout_ms_is_int(self) -> None:
        """KAFKA_REQUEST_TIMEOUT_MS should be an integer."""
        from omnibase_core.constants.constants_timeouts import KAFKA_REQUEST_TIMEOUT_MS

        assert isinstance(KAFKA_REQUEST_TIMEOUT_MS, int)


@pytest.mark.unit
class TestCacheTimeoutValues:
    """Tests for the expected values of cache timeout constants."""

    def test_default_cache_ttl_seconds_value(self) -> None:
        """DEFAULT_CACHE_TTL_SECONDS should be 300 seconds (5 minutes)."""
        from omnibase_core.constants.constants_timeouts import DEFAULT_CACHE_TTL_SECONDS

        assert DEFAULT_CACHE_TTL_SECONDS == 300

    def test_default_cache_ttl_is_positive(self) -> None:
        """DEFAULT_CACHE_TTL_SECONDS should be a positive value."""
        from omnibase_core.constants.constants_timeouts import DEFAULT_CACHE_TTL_SECONDS

        assert DEFAULT_CACHE_TTL_SECONDS > 0

    def test_default_cache_ttl_is_five_minutes(self) -> None:
        """DEFAULT_CACHE_TTL_SECONDS should represent 5 minutes in seconds."""
        from omnibase_core.constants.constants_timeouts import DEFAULT_CACHE_TTL_SECONDS

        five_minutes_in_seconds = 5 * 60
        assert DEFAULT_CACHE_TTL_SECONDS == five_minutes_in_seconds


@pytest.mark.unit
class TestCacheTimeoutTypes:
    """Tests for type validation of cache timeout constants."""

    def test_default_cache_ttl_seconds_is_int(self) -> None:
        """DEFAULT_CACHE_TTL_SECONDS should be an integer."""
        from omnibase_core.constants.constants_timeouts import DEFAULT_CACHE_TTL_SECONDS

        assert isinstance(DEFAULT_CACHE_TTL_SECONDS, int)


@pytest.mark.unit
class TestNewTimeoutConstantSemantics:
    """Tests for semantic correctness of new timeout constant definitions."""

    def test_thread_join_is_five_seconds(self) -> None:
        """THREAD_JOIN_TIMEOUT_SECONDS should represent 5 seconds."""
        from omnibase_core.constants.constants_timeouts import (
            THREAD_JOIN_TIMEOUT_SECONDS,
        )

        assert THREAD_JOIN_TIMEOUT_SECONDS == 5.0

    def test_process_shutdown_is_ten_seconds(self) -> None:
        """PROCESS_SHUTDOWN_TIMEOUT_SECONDS should represent 10 seconds."""
        from omnibase_core.constants.constants_timeouts import (
            PROCESS_SHUTDOWN_TIMEOUT_SECONDS,
        )

        assert PROCESS_SHUTDOWN_TIMEOUT_SECONDS == 10.0

    def test_http_request_is_thirty_seconds(self) -> None:
        """HTTP_REQUEST_TIMEOUT_SECONDS should represent 30 seconds."""
        from omnibase_core.constants.constants_timeouts import (
            HTTP_REQUEST_TIMEOUT_SECONDS,
        )

        assert HTTP_REQUEST_TIMEOUT_SECONDS == 30.0

    def test_kafka_request_is_five_seconds(self) -> None:
        """KAFKA_REQUEST_TIMEOUT_MS should represent 5 seconds in milliseconds."""
        from omnibase_core.constants.constants_timeouts import KAFKA_REQUEST_TIMEOUT_MS

        five_seconds_in_ms = 5 * 1000
        assert KAFKA_REQUEST_TIMEOUT_MS == five_seconds_in_ms

    def test_cache_ttl_is_five_minutes(self) -> None:
        """DEFAULT_CACHE_TTL_SECONDS should represent 5 minutes in seconds."""
        from omnibase_core.constants.constants_timeouts import DEFAULT_CACHE_TTL_SECONDS

        five_minutes_in_seconds = 5 * 60
        assert DEFAULT_CACHE_TTL_SECONDS == five_minutes_in_seconds
