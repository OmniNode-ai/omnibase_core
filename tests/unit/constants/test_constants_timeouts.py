# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

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
            "WEBSOCKET_PING_TIMEOUT_SECONDS",
            "DATABASE_QUERY_TIMEOUT_SECONDS",
            "FILE_IO_TIMEOUT_SECONDS",
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
            "WEBSOCKET_PING_TIMEOUT_SECONDS",
            "DATABASE_QUERY_TIMEOUT_SECONDS",
            "FILE_IO_TIMEOUT_SECONDS",
            "DEFAULT_CACHE_TTL_SECONDS",
        ]
        for export in expected_exports:
            assert export in __all__, f"{export} should be in __all__"

    def test_constants_timeouts_all_length(self) -> None:
        """__all__ should contain exactly 12 exports."""
        from omnibase_core.constants.constants_timeouts import __all__

        assert len(__all__) == 12


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
        assert five_minutes_in_seconds == DEFAULT_CACHE_TTL_SECONDS


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
        assert five_seconds_in_ms == KAFKA_REQUEST_TIMEOUT_MS

    def test_cache_ttl_is_five_minutes(self) -> None:
        """DEFAULT_CACHE_TTL_SECONDS should represent 5 minutes in seconds."""
        from omnibase_core.constants.constants_timeouts import DEFAULT_CACHE_TTL_SECONDS

        five_minutes_in_seconds = 5 * 60
        assert five_minutes_in_seconds == DEFAULT_CACHE_TTL_SECONDS


# =============================================================================
# Tests for WebSocket Timeout Constants
# =============================================================================


@pytest.mark.unit
class TestWebSocketTimeoutValues:
    """Tests for the expected values of WebSocket timeout constants."""

    def test_websocket_ping_timeout_seconds_value(self) -> None:
        """WEBSOCKET_PING_TIMEOUT_SECONDS should be 10.0 seconds."""
        from omnibase_core.constants.constants_timeouts import (
            WEBSOCKET_PING_TIMEOUT_SECONDS,
        )

        assert WEBSOCKET_PING_TIMEOUT_SECONDS == 10.0

    def test_websocket_ping_timeout_is_positive(self) -> None:
        """WEBSOCKET_PING_TIMEOUT_SECONDS should be a positive value."""
        from omnibase_core.constants.constants_timeouts import (
            WEBSOCKET_PING_TIMEOUT_SECONDS,
        )

        assert WEBSOCKET_PING_TIMEOUT_SECONDS > 0

    def test_websocket_ping_timeout_is_ten_seconds(self) -> None:
        """WEBSOCKET_PING_TIMEOUT_SECONDS should represent 10 seconds."""
        from omnibase_core.constants.constants_timeouts import (
            WEBSOCKET_PING_TIMEOUT_SECONDS,
        )

        ten_seconds = 10.0
        assert ten_seconds == WEBSOCKET_PING_TIMEOUT_SECONDS


@pytest.mark.unit
class TestWebSocketTimeoutTypes:
    """Tests for type validation of WebSocket timeout constants."""

    def test_websocket_ping_timeout_seconds_is_float(self) -> None:
        """WEBSOCKET_PING_TIMEOUT_SECONDS should be a float."""
        from omnibase_core.constants.constants_timeouts import (
            WEBSOCKET_PING_TIMEOUT_SECONDS,
        )

        assert isinstance(WEBSOCKET_PING_TIMEOUT_SECONDS, float)


@pytest.mark.unit
class TestWebSocketTimeoutPublicAPI:
    """Tests for WebSocket timeout constant public API exports."""

    def test_websocket_ping_timeout_exported_from_public_api(self) -> None:
        """WEBSOCKET_PING_TIMEOUT_SECONDS should be exported from omnibase_core.constants."""
        from omnibase_core.constants import WEBSOCKET_PING_TIMEOUT_SECONDS

        assert WEBSOCKET_PING_TIMEOUT_SECONDS == 10.0


# =============================================================================
# Tests for Database Timeout Constants
# =============================================================================


@pytest.mark.unit
class TestDatabaseTimeoutValues:
    """Tests for the expected values of database timeout constants."""

    def test_database_query_timeout_seconds_value(self) -> None:
        """DATABASE_QUERY_TIMEOUT_SECONDS should be 30.0 seconds."""
        from omnibase_core.constants.constants_timeouts import (
            DATABASE_QUERY_TIMEOUT_SECONDS,
        )

        assert DATABASE_QUERY_TIMEOUT_SECONDS == 30.0

    def test_database_query_timeout_is_positive(self) -> None:
        """DATABASE_QUERY_TIMEOUT_SECONDS should be a positive value."""
        from omnibase_core.constants.constants_timeouts import (
            DATABASE_QUERY_TIMEOUT_SECONDS,
        )

        assert DATABASE_QUERY_TIMEOUT_SECONDS > 0

    def test_database_query_timeout_is_thirty_seconds(self) -> None:
        """DATABASE_QUERY_TIMEOUT_SECONDS should represent 30 seconds."""
        from omnibase_core.constants.constants_timeouts import (
            DATABASE_QUERY_TIMEOUT_SECONDS,
        )

        thirty_seconds = 30.0
        assert thirty_seconds == DATABASE_QUERY_TIMEOUT_SECONDS

    def test_database_query_timeout_matches_http_timeout(self) -> None:
        """DATABASE_QUERY_TIMEOUT_SECONDS should equal HTTP_REQUEST_TIMEOUT_SECONDS.

        As documented, HTTP and database timeouts are equivalent (30s each).
        """
        from omnibase_core.constants.constants_timeouts import (
            DATABASE_QUERY_TIMEOUT_SECONDS,
            HTTP_REQUEST_TIMEOUT_SECONDS,
        )

        assert DATABASE_QUERY_TIMEOUT_SECONDS == HTTP_REQUEST_TIMEOUT_SECONDS

    def test_database_query_timeout_matches_default_ms_in_seconds(self) -> None:
        """DATABASE_QUERY_TIMEOUT_SECONDS should match TIMEOUT_DEFAULT_MS converted to seconds."""
        from omnibase_core.constants.constants_timeouts import (
            DATABASE_QUERY_TIMEOUT_SECONDS,
            TIMEOUT_DEFAULT_MS,
        )

        assert DATABASE_QUERY_TIMEOUT_SECONDS == TIMEOUT_DEFAULT_MS / 1000


@pytest.mark.unit
class TestDatabaseTimeoutTypes:
    """Tests for type validation of database timeout constants."""

    def test_database_query_timeout_seconds_is_float(self) -> None:
        """DATABASE_QUERY_TIMEOUT_SECONDS should be a float."""
        from omnibase_core.constants.constants_timeouts import (
            DATABASE_QUERY_TIMEOUT_SECONDS,
        )

        assert isinstance(DATABASE_QUERY_TIMEOUT_SECONDS, float)


@pytest.mark.unit
class TestDatabaseTimeoutPublicAPI:
    """Tests for database timeout constant public API exports."""

    def test_database_query_timeout_exported_from_public_api(self) -> None:
        """DATABASE_QUERY_TIMEOUT_SECONDS should be exported from omnibase_core.constants."""
        from omnibase_core.constants import DATABASE_QUERY_TIMEOUT_SECONDS

        assert DATABASE_QUERY_TIMEOUT_SECONDS == 30.0


# =============================================================================
# Tests for File I/O Timeout Constants
# =============================================================================


@pytest.mark.unit
class TestFileIOTimeoutValues:
    """Tests for the expected values of file I/O timeout constants."""

    def test_file_io_timeout_seconds_value(self) -> None:
        """FILE_IO_TIMEOUT_SECONDS should be 60.0 seconds."""
        from omnibase_core.constants.constants_timeouts import FILE_IO_TIMEOUT_SECONDS

        assert FILE_IO_TIMEOUT_SECONDS == 60.0

    def test_file_io_timeout_is_positive(self) -> None:
        """FILE_IO_TIMEOUT_SECONDS should be a positive value."""
        from omnibase_core.constants.constants_timeouts import FILE_IO_TIMEOUT_SECONDS

        assert FILE_IO_TIMEOUT_SECONDS > 0

    def test_file_io_timeout_is_sixty_seconds(self) -> None:
        """FILE_IO_TIMEOUT_SECONDS should represent 60 seconds (1 minute)."""
        from omnibase_core.constants.constants_timeouts import FILE_IO_TIMEOUT_SECONDS

        sixty_seconds = 60.0
        assert sixty_seconds == FILE_IO_TIMEOUT_SECONDS

    def test_file_io_timeout_is_one_minute(self) -> None:
        """FILE_IO_TIMEOUT_SECONDS should represent 1 minute."""
        from omnibase_core.constants.constants_timeouts import FILE_IO_TIMEOUT_SECONDS

        one_minute_in_seconds = 1 * 60.0
        assert one_minute_in_seconds == FILE_IO_TIMEOUT_SECONDS

    def test_file_io_timeout_greater_than_http_timeout(self) -> None:
        """FILE_IO_TIMEOUT_SECONDS should be greater than HTTP_REQUEST_TIMEOUT_SECONDS.

        As documented, file I/O (60s) > HTTP (30s) because disk can be slower.
        """
        from omnibase_core.constants.constants_timeouts import (
            FILE_IO_TIMEOUT_SECONDS,
            HTTP_REQUEST_TIMEOUT_SECONDS,
        )

        assert FILE_IO_TIMEOUT_SECONDS > HTTP_REQUEST_TIMEOUT_SECONDS

    def test_file_io_timeout_greater_than_database_timeout(self) -> None:
        """FILE_IO_TIMEOUT_SECONDS should be greater than DATABASE_QUERY_TIMEOUT_SECONDS.

        As documented, file I/O (60s) > database (30s).
        """
        from omnibase_core.constants.constants_timeouts import (
            DATABASE_QUERY_TIMEOUT_SECONDS,
            FILE_IO_TIMEOUT_SECONDS,
        )

        assert FILE_IO_TIMEOUT_SECONDS > DATABASE_QUERY_TIMEOUT_SECONDS

    def test_file_io_timeout_is_2x_http_timeout(self) -> None:
        """FILE_IO_TIMEOUT_SECONDS should be 2x HTTP_REQUEST_TIMEOUT_SECONDS.

        As documented in the module: FILE_IO (60s) = 2x HTTP (30s).
        """
        from omnibase_core.constants.constants_timeouts import (
            FILE_IO_TIMEOUT_SECONDS,
            HTTP_REQUEST_TIMEOUT_SECONDS,
        )

        assert FILE_IO_TIMEOUT_SECONDS == 2 * HTTP_REQUEST_TIMEOUT_SECONDS


@pytest.mark.unit
class TestFileIOTimeoutTypes:
    """Tests for type validation of file I/O timeout constants."""

    def test_file_io_timeout_seconds_is_float(self) -> None:
        """FILE_IO_TIMEOUT_SECONDS should be a float."""
        from omnibase_core.constants.constants_timeouts import FILE_IO_TIMEOUT_SECONDS

        assert isinstance(FILE_IO_TIMEOUT_SECONDS, float)


@pytest.mark.unit
class TestFileIOTimeoutPublicAPI:
    """Tests for file I/O timeout constant public API exports."""

    def test_file_io_timeout_exported_from_public_api(self) -> None:
        """FILE_IO_TIMEOUT_SECONDS should be exported from omnibase_core.constants."""
        from omnibase_core.constants import FILE_IO_TIMEOUT_SECONDS

        assert FILE_IO_TIMEOUT_SECONDS == 60.0


# =============================================================================
# Tests for Network Timeout Ordering
# =============================================================================


@pytest.mark.unit
class TestNetworkTimeoutOrdering:
    """Tests for the documented network timeout ordering relationships.

    The module documents the following ordering:
    KAFKA (5s) < WEBSOCKET (10s) < HTTP (30s) = DATABASE (30s) < FILE (60s)

    Rationale: Real-time protocols (Kafka, WebSocket) expect faster responses
    than request/response protocols (HTTP). Database matches HTTP since API
    calls often include DB queries. File I/O is slowest due to disk variability.
    """

    def test_kafka_less_than_websocket(self) -> None:
        """KAFKA_REQUEST_TIMEOUT_MS should be less than WEBSOCKET_PING_TIMEOUT_SECONDS.

        Kafka (5s) < WebSocket (10s) because Kafka is designed for
        low-latency streaming with faster failover requirements.
        """
        from omnibase_core.constants.constants_timeouts import (
            KAFKA_REQUEST_TIMEOUT_MS,
            WEBSOCKET_PING_TIMEOUT_SECONDS,
        )

        # Convert Kafka timeout to seconds for comparison
        kafka_timeout_seconds = KAFKA_REQUEST_TIMEOUT_MS / 1000
        assert kafka_timeout_seconds < WEBSOCKET_PING_TIMEOUT_SECONDS

    def test_websocket_less_than_http(self) -> None:
        """WEBSOCKET_PING_TIMEOUT_SECONDS should be less than HTTP_REQUEST_TIMEOUT_SECONDS.

        WebSocket (10s) < HTTP (30s) because WebSocket is a streaming
        protocol that expects lower latency than request/response HTTP.
        """
        from omnibase_core.constants.constants_timeouts import (
            HTTP_REQUEST_TIMEOUT_SECONDS,
            WEBSOCKET_PING_TIMEOUT_SECONDS,
        )

        assert WEBSOCKET_PING_TIMEOUT_SECONDS < HTTP_REQUEST_TIMEOUT_SECONDS

    def test_http_equals_database(self) -> None:
        """HTTP_REQUEST_TIMEOUT_SECONDS should equal DATABASE_QUERY_TIMEOUT_SECONDS.

        HTTP (30s) == Database (30s) because API calls often include
        database queries, so they share the same default timeout.
        """
        from omnibase_core.constants.constants_timeouts import (
            DATABASE_QUERY_TIMEOUT_SECONDS,
            HTTP_REQUEST_TIMEOUT_SECONDS,
        )

        assert HTTP_REQUEST_TIMEOUT_SECONDS == DATABASE_QUERY_TIMEOUT_SECONDS

    def test_database_less_than_file_io(self) -> None:
        """DATABASE_QUERY_TIMEOUT_SECONDS should be less than FILE_IO_TIMEOUT_SECONDS.

        Database (30s) < File I/O (60s) because disk I/O can be slower
        than network operations, especially on network-mounted filesystems.
        """
        from omnibase_core.constants.constants_timeouts import (
            DATABASE_QUERY_TIMEOUT_SECONDS,
            FILE_IO_TIMEOUT_SECONDS,
        )

        assert DATABASE_QUERY_TIMEOUT_SECONDS < FILE_IO_TIMEOUT_SECONDS

    def test_full_network_ordering(self) -> None:
        """Full network timeout ordering: KAFKA < WEBSOCKET < HTTP = DB < FILE.

        This test verifies the complete ordering documented in the module.
        """
        from omnibase_core.constants.constants_timeouts import (
            DATABASE_QUERY_TIMEOUT_SECONDS,
            FILE_IO_TIMEOUT_SECONDS,
            HTTP_REQUEST_TIMEOUT_SECONDS,
            KAFKA_REQUEST_TIMEOUT_MS,
            WEBSOCKET_PING_TIMEOUT_SECONDS,
        )

        # Convert Kafka to seconds for comparison
        kafka_seconds = KAFKA_REQUEST_TIMEOUT_MS / 1000

        # Verify ordering
        assert kafka_seconds < WEBSOCKET_PING_TIMEOUT_SECONDS
        assert WEBSOCKET_PING_TIMEOUT_SECONDS < HTTP_REQUEST_TIMEOUT_SECONDS
        assert HTTP_REQUEST_TIMEOUT_SECONDS == DATABASE_QUERY_TIMEOUT_SECONDS
        assert DATABASE_QUERY_TIMEOUT_SECONDS < FILE_IO_TIMEOUT_SECONDS

    def test_all_network_timeouts_are_positive(self) -> None:
        """All network-related timeout constants should be positive values."""
        from omnibase_core.constants.constants_timeouts import (
            DATABASE_QUERY_TIMEOUT_SECONDS,
            FILE_IO_TIMEOUT_SECONDS,
            HTTP_REQUEST_TIMEOUT_SECONDS,
            KAFKA_REQUEST_TIMEOUT_MS,
            WEBSOCKET_PING_TIMEOUT_SECONDS,
        )

        assert KAFKA_REQUEST_TIMEOUT_MS > 0
        assert WEBSOCKET_PING_TIMEOUT_SECONDS > 0
        assert HTTP_REQUEST_TIMEOUT_SECONDS > 0
        assert DATABASE_QUERY_TIMEOUT_SECONDS > 0
        assert FILE_IO_TIMEOUT_SECONDS > 0


# =============================================================================
# Tests for Unit Equivalences
# =============================================================================


@pytest.mark.unit
class TestTimeoutUnitEquivalences:
    """Tests for documented unit equivalences between constants.

    The module documents these equivalences:
    - TIMEOUT_DEFAULT_MS (30,000ms) == HTTP_REQUEST_TIMEOUT_SECONDS (30s)
    - TIMEOUT_DEFAULT_MS (30,000ms) == DATABASE_QUERY_TIMEOUT_SECONDS (30s)
    - TIMEOUT_LONG_MS (300,000ms) == DEFAULT_CACHE_TTL_SECONDS (300s)
    """

    def test_default_ms_equals_http_seconds(self) -> None:
        """TIMEOUT_DEFAULT_MS should equal HTTP_REQUEST_TIMEOUT_SECONDS when converted."""
        from omnibase_core.constants.constants_timeouts import (
            HTTP_REQUEST_TIMEOUT_SECONDS,
            TIMEOUT_DEFAULT_MS,
        )

        assert TIMEOUT_DEFAULT_MS / 1000 == HTTP_REQUEST_TIMEOUT_SECONDS

    def test_default_ms_equals_database_seconds(self) -> None:
        """TIMEOUT_DEFAULT_MS should equal DATABASE_QUERY_TIMEOUT_SECONDS when converted."""
        from omnibase_core.constants.constants_timeouts import (
            DATABASE_QUERY_TIMEOUT_SECONDS,
            TIMEOUT_DEFAULT_MS,
        )

        assert TIMEOUT_DEFAULT_MS / 1000 == DATABASE_QUERY_TIMEOUT_SECONDS

    def test_long_ms_equals_cache_ttl_seconds(self) -> None:
        """TIMEOUT_LONG_MS should equal DEFAULT_CACHE_TTL_SECONDS when converted.

        Both represent 5 minutes (300 seconds / 300,000 ms).
        """
        from omnibase_core.constants.constants_timeouts import (
            DEFAULT_CACHE_TTL_SECONDS,
            TIMEOUT_LONG_MS,
        )

        assert TIMEOUT_LONG_MS / 1000 == DEFAULT_CACHE_TTL_SECONDS

    def test_websocket_equals_process_shutdown(self) -> None:
        """WEBSOCKET_PING_TIMEOUT_SECONDS should equal PROCESS_SHUTDOWN_TIMEOUT_SECONDS.

        As noted in the module documentation, this is coincidental but both are 10 seconds.
        """
        from omnibase_core.constants.constants_timeouts import (
            PROCESS_SHUTDOWN_TIMEOUT_SECONDS,
            WEBSOCKET_PING_TIMEOUT_SECONDS,
        )

        assert WEBSOCKET_PING_TIMEOUT_SECONDS == PROCESS_SHUTDOWN_TIMEOUT_SECONDS


# =============================================================================
# Tests for Timeout Boundary Conditions
# =============================================================================


@pytest.mark.unit
class TestTimeoutBoundaryConditions:
    """Tests for boundary conditions and edge cases of timeout constants.

    These tests verify that timeout values are within reasonable bounds
    and follow the documented constraints.
    """

    def test_all_timeouts_within_bounds_ms(self) -> None:
        """All millisecond timeout constants should be within MIN and MAX bounds."""
        from omnibase_core.constants.constants_timeouts import (
            KAFKA_REQUEST_TIMEOUT_MS,
            TIMEOUT_DEFAULT_MS,
            TIMEOUT_LONG_MS,
            TIMEOUT_MAX_MS,
            TIMEOUT_MIN_MS,
        )

        # All ms-based timeouts should be >= MIN and <= MAX
        ms_timeouts = [TIMEOUT_DEFAULT_MS, TIMEOUT_LONG_MS, KAFKA_REQUEST_TIMEOUT_MS]
        for timeout in ms_timeouts:
            assert timeout >= TIMEOUT_MIN_MS, f"{timeout} should be >= {TIMEOUT_MIN_MS}"
            assert timeout <= TIMEOUT_MAX_MS, f"{timeout} should be <= {TIMEOUT_MAX_MS}"

    def test_all_second_timeouts_within_bounds(self) -> None:
        """All second-based timeout constants should be within MIN and MAX bounds."""
        from omnibase_core.constants.constants_timeouts import (
            DATABASE_QUERY_TIMEOUT_SECONDS,
            FILE_IO_TIMEOUT_SECONDS,
            HTTP_REQUEST_TIMEOUT_SECONDS,
            PROCESS_SHUTDOWN_TIMEOUT_SECONDS,
            THREAD_JOIN_TIMEOUT_SECONDS,
            TIMEOUT_MAX_MS,
            TIMEOUT_MIN_MS,
            WEBSOCKET_PING_TIMEOUT_SECONDS,
        )

        # Convert bounds to seconds
        min_seconds = TIMEOUT_MIN_MS / 1000
        max_seconds = TIMEOUT_MAX_MS / 1000

        second_timeouts = [
            THREAD_JOIN_TIMEOUT_SECONDS,
            PROCESS_SHUTDOWN_TIMEOUT_SECONDS,
            HTTP_REQUEST_TIMEOUT_SECONDS,
            WEBSOCKET_PING_TIMEOUT_SECONDS,
            DATABASE_QUERY_TIMEOUT_SECONDS,
            FILE_IO_TIMEOUT_SECONDS,
        ]
        for timeout in second_timeouts:
            assert timeout >= min_seconds, f"{timeout}s should be >= {min_seconds}s"
            assert timeout <= max_seconds, f"{timeout}s should be <= {max_seconds}s"

    def test_file_io_less_than_long_timeout(self) -> None:
        """FILE_IO_TIMEOUT_SECONDS should be less than TIMEOUT_LONG_MS.

        As documented, file operations shouldn't need the full 5-minute
        long timeout - that's reserved for complex workflows.
        """
        from omnibase_core.constants.constants_timeouts import (
            FILE_IO_TIMEOUT_SECONDS,
            TIMEOUT_LONG_MS,
        )

        long_timeout_seconds = TIMEOUT_LONG_MS / 1000
        assert long_timeout_seconds > FILE_IO_TIMEOUT_SECONDS

    def test_thread_join_is_half_process_shutdown(self) -> None:
        """THREAD_JOIN_TIMEOUT_SECONDS should be half of PROCESS_SHUTDOWN_TIMEOUT_SECONDS.

        As documented, thread join (5s) = 50% of process shutdown (10s)
        to provide buffer for thread cleanup before process terminates.
        """
        from omnibase_core.constants.constants_timeouts import (
            PROCESS_SHUTDOWN_TIMEOUT_SECONDS,
            THREAD_JOIN_TIMEOUT_SECONDS,
        )

        assert THREAD_JOIN_TIMEOUT_SECONDS == PROCESS_SHUTDOWN_TIMEOUT_SECONDS / 2

    def test_timeout_long_is_10x_default(self) -> None:
        """TIMEOUT_LONG_MS should be 10x TIMEOUT_DEFAULT_MS.

        As documented in the module relationships.
        """
        from omnibase_core.constants.constants_timeouts import (
            TIMEOUT_DEFAULT_MS,
            TIMEOUT_LONG_MS,
        )

        assert TIMEOUT_LONG_MS == 10 * TIMEOUT_DEFAULT_MS

    def test_timeout_max_is_2x_long(self) -> None:
        """TIMEOUT_MAX_MS should be 2x TIMEOUT_LONG_MS.

        As documented in the module relationships.
        """
        from omnibase_core.constants.constants_timeouts import (
            TIMEOUT_LONG_MS,
            TIMEOUT_MAX_MS,
        )

        assert TIMEOUT_MAX_MS == 2 * TIMEOUT_LONG_MS
