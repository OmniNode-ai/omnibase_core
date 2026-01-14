"""Tests for ServiceEffectMockRegistry.

Part of OMN-1147: Effect Classification System test suite.
"""

from datetime import datetime
from typing import Any

import pytest

from omnibase_core.services.replay.service_effect_mock_registry import (
    ServiceEffectMockRegistry,
)


@pytest.mark.unit
class TestServiceEffectMockRegistry:
    """Test cases for ServiceEffectMockRegistry service."""

    def test_register_mock_and_get_mock(self) -> None:
        """Test register_mock() and get_mock() basic functionality."""
        registry = ServiceEffectMockRegistry()

        mock_fn = lambda: 42  # noqa: E731
        registry.register_mock("test.effect", mock_fn)

        retrieved = registry.get_mock("test.effect")
        assert retrieved is mock_fn
        assert retrieved() == 42

    def test_has_mock_returns_true_for_registered(self) -> None:
        """Test has_mock() returns True for registered mocks."""
        registry = ServiceEffectMockRegistry()
        registry.register_mock("time.now", lambda: datetime(2025, 1, 1))

        assert registry.has_mock("time.now") is True

    def test_has_mock_returns_false_for_unregistered(self) -> None:
        """Test has_mock() returns False for unregistered effect keys."""
        registry = ServiceEffectMockRegistry()

        assert registry.has_mock("nonexistent.effect") is False
        assert registry.has_mock("") is False

    def test_unregister_mock_removes_mock(self) -> None:
        """Test unregister_mock() removes a registered mock."""
        registry = ServiceEffectMockRegistry()
        registry.register_mock("test.effect", lambda: "value")

        assert registry.has_mock("test.effect") is True

        result = registry.unregister_mock("test.effect")

        assert result is True
        assert registry.has_mock("test.effect") is False
        assert registry.get_mock("test.effect") is None

    def test_unregister_mock_returns_false_for_nonexistent(self) -> None:
        """Test unregister_mock() returns False for non-existent keys."""
        registry = ServiceEffectMockRegistry()

        result = registry.unregister_mock("nonexistent.effect")

        assert result is False

    def test_clear_removes_all_mocks(self) -> None:
        """Test clear() removes all registered mocks."""
        registry = ServiceEffectMockRegistry()
        registry.register_mock("effect1", lambda: 1)
        registry.register_mock("effect2", lambda: 2)
        registry.register_mock("effect3", lambda: 3)

        assert registry.mock_count == 3

        registry.clear()

        assert registry.mock_count == 0
        assert registry.has_mock("effect1") is False
        assert registry.has_mock("effect2") is False
        assert registry.has_mock("effect3") is False

    def test_list_registered_effects_returns_sorted_keys(self) -> None:
        """Test list_registered_effects() returns sorted list of keys."""
        registry = ServiceEffectMockRegistry()
        registry.register_mock("z.last", lambda: None)
        registry.register_mock("a.first", lambda: None)
        registry.register_mock("m.middle", lambda: None)

        effects = registry.list_registered_effects()

        assert effects == ["a.first", "m.middle", "z.last"]

    def test_list_registered_effects_empty_registry(self) -> None:
        """Test list_registered_effects() returns empty list when no mocks."""
        registry = ServiceEffectMockRegistry()

        effects = registry.list_registered_effects()

        assert effects == []

    def test_mock_count_property(self) -> None:
        """Test mock_count property returns correct count."""
        registry = ServiceEffectMockRegistry()

        assert registry.mock_count == 0

        registry.register_mock("effect1", lambda: 1)
        assert registry.mock_count == 1

        registry.register_mock("effect2", lambda: 2)
        assert registry.mock_count == 2

        registry.unregister_mock("effect1")
        assert registry.mock_count == 1

    def test_validation_empty_key_raises_error(self) -> None:
        """Test that empty effect_key raises ValueError."""
        registry = ServiceEffectMockRegistry()

        with pytest.raises(ValueError, match="empty"):
            registry.register_mock("", lambda: None)

    def test_validation_whitespace_key_raises_error(self) -> None:
        """Test that whitespace-only effect_key raises ValueError."""
        registry = ServiceEffectMockRegistry()

        with pytest.raises(ValueError, match="empty"):
            registry.register_mock("   ", lambda: None)

        with pytest.raises(ValueError, match="empty"):
            registry.register_mock("\t\n", lambda: None)

    def test_validation_non_callable_raises_error(self) -> None:
        """Test that non-callable mock_callable raises ValueError."""
        registry = ServiceEffectMockRegistry()

        with pytest.raises(ValueError, match="callable"):
            registry.register_mock("test.effect", "not a callable")  # type: ignore[arg-type]

        with pytest.raises(ValueError, match="callable"):
            registry.register_mock("test.effect", 42)  # type: ignore[arg-type]

        with pytest.raises(ValueError, match="callable"):
            registry.register_mock("test.effect", None)  # type: ignore[arg-type]

    def test_overwriting_existing_mock(self) -> None:
        """Test that registering a mock for existing key overwrites it."""
        registry = ServiceEffectMockRegistry()

        registry.register_mock("test.effect", lambda: "original")
        assert registry.get_mock("test.effect")() == "original"

        registry.register_mock("test.effect", lambda: "updated")
        assert registry.get_mock("test.effect")() == "updated"

        # Still only one mock
        assert registry.mock_count == 1

    def test_get_mock_returns_none_for_nonexistent(self) -> None:
        """Test get_mock() returns None for non-existent keys."""
        registry = ServiceEffectMockRegistry()

        assert registry.get_mock("nonexistent") is None

    def test_mock_with_arguments(self) -> None:
        """Test mock callable can accept arguments."""
        registry = ServiceEffectMockRegistry()

        def mock_http_get(url: str, **kwargs: Any) -> dict[str, Any]:
            return {"status": 200, "url": url, "params": kwargs}

        registry.register_mock("network.http_get", mock_http_get)

        mock_fn = registry.get_mock("network.http_get")
        assert mock_fn is not None

        result = mock_fn("https://api.example.com", timeout=30)
        assert result["status"] == 200
        assert result["url"] == "https://api.example.com"
        assert result["params"]["timeout"] == 30

    def test_mock_with_return_value(self) -> None:
        """Test mock returns expected values."""
        registry = ServiceEffectMockRegistry()

        fixed_time = datetime(2025, 1, 1, 12, 0, 0)
        registry.register_mock("time.now", lambda: fixed_time)

        mock_fn = registry.get_mock("time.now")
        assert mock_fn is not None
        assert mock_fn() == fixed_time

    def test_str_representation(self) -> None:
        """Test __str__ returns human-readable summary."""
        registry = ServiceEffectMockRegistry()
        registry.register_mock("a", lambda: None)
        registry.register_mock("b", lambda: None)

        str_repr = str(registry)

        assert "ServiceEffectMockRegistry" in str_repr
        assert "2" in str_repr  # mock count

    def test_repr_representation(self) -> None:
        """Test __repr__ returns detailed representation."""
        registry = ServiceEffectMockRegistry()
        registry.register_mock("effect.one", lambda: None)
        registry.register_mock("effect.two", lambda: None)

        repr_str = repr(registry)

        assert "ServiceEffectMockRegistry" in repr_str
        assert "effect.one" in repr_str or "effects" in repr_str

    def test_repr_truncates_many_effects(self) -> None:
        """Test __repr__ truncates when many effects registered."""
        registry = ServiceEffectMockRegistry()

        # Register more than 10 effects
        for i in range(15):
            registry.register_mock(f"effect.{i:02d}", lambda: None)

        repr_str = repr(registry)

        assert "ServiceEffectMockRegistry" in repr_str
        assert "15" in repr_str  # Should show count

    def test_registry_isolation(self) -> None:
        """Test that separate registry instances are isolated."""
        registry1 = ServiceEffectMockRegistry()
        registry2 = ServiceEffectMockRegistry()

        registry1.register_mock("shared.key", lambda: "registry1")

        assert registry1.has_mock("shared.key") is True
        assert registry2.has_mock("shared.key") is False

    def test_callable_class_instance(self) -> None:
        """Test that callable class instances can be registered as mocks."""

        class MockCallable:
            def __init__(self, return_value: str) -> None:
                self.return_value = return_value

            def __call__(self) -> str:
                return self.return_value

        registry = ServiceEffectMockRegistry()
        mock_instance = MockCallable("mocked_result")

        registry.register_mock("test.callable", mock_instance)

        retrieved = registry.get_mock("test.callable")
        assert retrieved is not None
        assert retrieved() == "mocked_result"

    def test_lambda_with_closure(self) -> None:
        """Test lambda with closure captures expected values."""
        registry = ServiceEffectMockRegistry()

        captured_value = {"count": 0}

        def mock_fn() -> int:
            captured_value["count"] += 1
            return captured_value["count"]

        registry.register_mock("counter", mock_fn)

        mock = registry.get_mock("counter")
        assert mock is not None
        assert mock() == 1
        assert mock() == 2
        assert mock() == 3

    def test_async_mock_can_be_registered(self) -> None:
        """Test that async functions can be registered as mocks."""
        registry = ServiceEffectMockRegistry()

        async def async_mock() -> str:
            return "async_result"

        # Async functions are callable
        registry.register_mock("async.effect", async_mock)

        retrieved = registry.get_mock("async.effect")
        assert retrieved is async_mock

    def test_dot_notation_keys(self) -> None:
        """Test that dot-notation effect keys work correctly."""
        registry = ServiceEffectMockRegistry()

        registry.register_mock("network.http.get", lambda: "get")
        registry.register_mock("network.http.post", lambda: "post")
        registry.register_mock("database.postgres.query", lambda: "query")

        assert registry.has_mock("network.http.get") is True
        assert registry.has_mock("network.http.post") is True
        assert registry.has_mock("database.postgres.query") is True

        # Partial keys should not match
        assert registry.has_mock("network") is False
        assert registry.has_mock("network.http") is False

    def test_clear_on_empty_registry(self) -> None:
        """Test clear() on empty registry doesn't raise error."""
        registry = ServiceEffectMockRegistry()

        # Should not raise
        registry.clear()

        assert registry.mock_count == 0
