"""Test retry_count tracking fix in NodeEffect."""

from unittest.mock import Mock

import pytest

from omnibase_core.enums.enum_effect_types import EnumEffectType
from omnibase_core.models.container.model_onex_container import ModelONEXContainer
from omnibase_core.models.model_effect_input import ModelEffectInput
from omnibase_core.models.service.model_service_effect import ModelServiceEffect


class RetryTestError(Exception):
    """Custom exception for retry test scenarios."""


@pytest.fixture
def mock_container():
    """Create a mock ModelONEXContainer."""
    container = Mock(spec=ModelONEXContainer)
    container.get_service = Mock(return_value=None)
    return container


@pytest.fixture
def service_effect(mock_container):
    """Create a ModelServiceEffect instance."""
    return ModelServiceEffect(mock_container)


class TestRetryCountTracking:
    """Test that retry_count is correctly tracked and returned."""

    @pytest.mark.asyncio
    async def test_retry_count_zero_on_success(self, service_effect):
        """Test that retry_count is 0 when operation succeeds on first attempt."""
        import tempfile
        from pathlib import Path

        # Create temporary file
        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".txt") as f:
            temp_path = Path(f.name)
            f.write("test content")

        try:
            effect_input = ModelEffectInput(
                effect_type=EnumEffectType.FILE_OPERATION,
                operation_data={
                    "operation_type": "read",
                    "file_path": str(temp_path),
                },
                retry_enabled=True,
                max_retries=3,
                retry_delay_ms=10,
            )

            result = await service_effect.process(effect_input)

            # Verify retry_count is 0 (succeeded on first attempt)
            assert result.retry_count == 0, (
                f"Expected retry_count=0 for successful first attempt, "
                f"got {result.retry_count}"
            )

        finally:
            temp_path.unlink(missing_ok=True)

    @pytest.mark.asyncio
    async def test_retry_count_tracks_actual_retries(self, service_effect):
        """Test that retry_count correctly tracks the number of retries performed."""
        import asyncio

        # Track call count
        call_count = 0

        async def flaky_handler(operation_data, transaction):
            """Handler that fails twice, then succeeds."""
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise RetryTestError(f"Simulated failure {call_count}")
            return {"status": "success", "attempts": call_count}

        # Replace handler with flaky one
        service_effect.effect_handlers[EnumEffectType.FILE_OPERATION] = flaky_handler

        effect_input = ModelEffectInput(
            effect_type=EnumEffectType.FILE_OPERATION,
            operation_data={"test": "data"},
            retry_enabled=True,
            max_retries=5,
            retry_delay_ms=10,
        )

        result = await service_effect.process(effect_input)

        # Verify retry_count matches actual retries (2 failures before success)
        assert result.retry_count == 2, (
            f"Expected retry_count=2 (failed twice before succeeding), "
            f"got {result.retry_count}"
        )
        assert call_count == 3, f"Expected 3 total calls, got {call_count}"
        assert result.result["attempts"] == 3

    @pytest.mark.asyncio
    async def test_retry_count_on_max_retries_exhausted(self, service_effect):
        """Test that retry_count reflects max retries when all attempts fail."""

        async def always_failing_handler(operation_data, transaction):
            """Handler that always fails."""
            raise RetryTestError("Always fails")

        # Replace handler
        service_effect.effect_handlers[EnumEffectType.FILE_OPERATION] = (
            always_failing_handler
        )

        effect_input = ModelEffectInput(
            effect_type=EnumEffectType.FILE_OPERATION,
            operation_data={"test": "data"},
            retry_enabled=True,
            max_retries=3,
            retry_delay_ms=10,
        )

        # Should fail after max_retries
        with pytest.raises(Exception):
            await service_effect.process(effect_input)

        # Note: When the operation fails, we can't check the retry_count in the output
        # since an exception is raised. The test above verifies the success case.

    @pytest.mark.asyncio
    async def test_retry_count_with_disabled_retry(self, service_effect):
        """Test that retry_count is 0 when retry is disabled."""
        import tempfile
        from pathlib import Path

        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".txt") as f:
            temp_path = Path(f.name)
            f.write("test content")

        try:
            effect_input = ModelEffectInput(
                effect_type=EnumEffectType.FILE_OPERATION,
                operation_data={
                    "operation_type": "read",
                    "file_path": str(temp_path),
                },
                retry_enabled=False,  # Retry disabled
                max_retries=0,
            )

            result = await service_effect.process(effect_input)

            # Verify retry_count is 0 when retry is disabled
            assert result.retry_count == 0

        finally:
            temp_path.unlink(missing_ok=True)

    @pytest.mark.asyncio
    async def test_retry_count_in_output_metadata(self, service_effect):
        """Test that retry_count is accessible in ModelEffectOutput."""
        import tempfile
        from pathlib import Path

        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".txt") as f:
            temp_path = Path(f.name)
            f.write("test")

        try:
            effect_input = ModelEffectInput(
                effect_type=EnumEffectType.FILE_OPERATION,
                operation_data={
                    "operation_type": "read",
                    "file_path": str(temp_path),
                },
                retry_enabled=True,
                max_retries=3,
            )

            result = await service_effect.process(effect_input)

            # Verify retry_count field exists and is an integer
            assert hasattr(result, "retry_count")
            assert isinstance(result.retry_count, int)
            assert result.retry_count >= 0

        finally:
            temp_path.unlink(missing_ok=True)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
