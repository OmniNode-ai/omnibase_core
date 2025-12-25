"""Thread safety, async-safe, and UUID preservation tests for ModelReducerOutput[T].

This module provides comprehensive concurrency and serialization tests for
ModelReducerOutput, including:
- Thread safety validation (multiple threads accessing same instance)
- Async-safe behavior (asyncio task concurrent access)
- UUID format preservation through serialization cycles

These tests complement the main test_model_reducer_output.py file and specifically
validate the model's behavior under concurrent access patterns.

Reference: docs/guides/THREADING.md - Thread Safety Guidelines
"""

import asyncio
import threading
from concurrent.futures import ThreadPoolExecutor
from uuid import UUID, uuid4

import pytest
from pydantic import ValidationError

from omnibase_core.enums.enum_reducer_types import EnumReductionType
from omnibase_core.models.common.model_reducer_metadata import ModelReducerMetadata
from omnibase_core.models.reducer.model_intent import ModelIntent
from omnibase_core.models.reducer.model_reducer_output import ModelReducerOutput
from omnibase_core.models.reducer.payloads import ModelPayloadLogEvent

pytestmark = pytest.mark.unit


@pytest.mark.unit
class TestModelReducerOutputThreadSafety:
    """Test thread safety of ModelReducerOutput via immutability.

    Validates that ModelReducerOutput instances are safe to access concurrently
    from multiple threads, as required by pytest-xdist parallel execution and
    concurrent processing scenarios.

    Reference: docs/guides/THREADING.md - Thread Safety Guidelines
    """

    def test_concurrent_read_access_from_multiple_threads(self):
        """Test that multiple threads can safely read from the same instance.

        Validates that concurrent read operations from 10+ threads do not cause
        race conditions, data corruption, or access violations."""
        # Create a single instance with intents
        intent = ModelIntent(
            intent_type="log",
            target="service",
            payload=ModelPayloadLogEvent(
                level="INFO",
                message="Test message",
            ),
        )
        output = ModelReducerOutput[int](
            result=42,
            operation_id=uuid4(),
            reduction_type=EnumReductionType.AGGREGATE,
            processing_time_ms=15.5,
            items_processed=100,
            conflicts_resolved=5,
            intents=(intent,),
        )

        results = []
        errors = []

        def read_fields():
            """Read all fields from the instance."""
            try:
                # Read all fields multiple times
                for _ in range(10):
                    _ = output.result
                    _ = output.operation_id
                    _ = output.reduction_type
                    _ = output.processing_time_ms
                    _ = output.items_processed
                    _ = output.conflicts_resolved
                    _ = output.intents
                    _ = output.metadata
                    _ = output.timestamp
                results.append(True)
            except Exception as e:
                errors.append(e)

        # Launch 15 threads to read concurrently
        threads = [threading.Thread(target=read_fields) for _ in range(15)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()

        # Validate no errors occurred
        assert len(errors) == 0, f"Errors during concurrent reads: {errors}"
        assert len(results) == 15, "Not all threads completed successfully"

    def test_concurrent_read_with_thread_pool(self):
        """Test concurrent reads using ThreadPoolExecutor.

        Validates that the model is safe to access from a thread pool,
        which is a common pattern in production systems."""
        output = ModelReducerOutput[str](
            result="aggregation_complete",
            operation_id=uuid4(),
            reduction_type=EnumReductionType.ACCUMULATE,
            processing_time_ms=8.2,
            items_processed=50,
        )

        def access_model(iteration: int) -> tuple:
            """Access model fields and return values."""
            return (
                iteration,
                output.result,
                output.reduction_type,
                output.items_processed,
                output.processing_time_ms,
            )

        # Use thread pool to access model concurrently
        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(access_model, i) for i in range(20)]
            results = [future.result() for future in futures]

        # Validate all accesses succeeded
        assert len(results) == 20
        # Validate data consistency across all threads
        for (
            iteration,
            result,
            reduction_type,
            items_processed,
            processing_time,
        ) in results:
            assert result == "aggregation_complete"
            assert reduction_type == EnumReductionType.ACCUMULATE
            assert items_processed == 50
            assert processing_time == 8.2

    def test_immutability_prevents_race_conditions(self):
        """Test that immutability prevents write-based race conditions.

        Validates that the frozen model prevents concurrent modification attempts,
        ensuring thread safety through immutability."""
        output = ModelReducerOutput[int](
            result=42,
            operation_id=uuid4(),
            reduction_type=EnumReductionType.FOLD,
            processing_time_ms=10.0,
            items_processed=5,
        )

        errors = []

        def attempt_modification():
            """Attempt to modify fields (should fail)."""
            try:
                output.result = 100  # type: ignore[misc]
            except ValidationError:
                errors.append("result_modification_blocked")

            try:
                output.items_processed = 10  # type: ignore[misc]
            except ValidationError:
                errors.append("items_processed_modification_blocked")

        # Launch multiple threads attempting modifications
        threads = [threading.Thread(target=attempt_modification) for _ in range(5)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()

        # All modification attempts should be blocked
        assert len(errors) == 10  # 5 threads × 2 fields

    def test_serialization_thread_safety(self):
        """Test that serialization is thread-safe.

        Validates that multiple threads can serialize the same instance
        concurrently without corruption or deadlocks."""
        output = ModelReducerOutput[dict](
            result={"total": 500, "count": 10},
            operation_id=uuid4(),
            reduction_type=EnumReductionType.MERGE,
            processing_time_ms=25.5,
            items_processed=300,
        )

        serialized_results = []
        errors = []

        def serialize_model():
            """Serialize model to dict and JSON."""
            try:
                dict_result = output.model_dump()
                json_result = output.model_dump_json()
                serialized_results.append((dict_result, json_result))
            except Exception as e:
                errors.append(e)

        # Launch threads to serialize concurrently
        threads = [threading.Thread(target=serialize_model) for _ in range(12)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()

        # Validate no errors and all serializations succeeded
        assert len(errors) == 0, f"Serialization errors: {errors}"
        assert len(serialized_results) == 12

        # Validate all serializations are identical
        first_dict = serialized_results[0][0]
        for dict_result, _ in serialized_results:
            assert dict_result["result"] == first_dict["result"]
            assert dict_result["reduction_type"] == first_dict["reduction_type"]


@pytest.mark.unit
class TestModelReducerOutputAsyncSafe:
    """Test async-safe behavior of ModelReducerOutput.

    Validates that ModelReducerOutput instances can be safely used in async
    contexts, including concurrent asyncio tasks and event loop scenarios.

    Reference: docs/guides/THREADING.md - Async Safety Guidelines
    """

    @pytest.mark.asyncio
    async def test_concurrent_async_read_access(self):
        """Test concurrent access from multiple asyncio tasks.

        Validates that multiple async tasks can safely read from the same
        instance without event loop conflicts or coroutine interference."""
        output = ModelReducerOutput[int](
            result=999,
            operation_id=uuid4(),
            reduction_type=EnumReductionType.FOLD,
            processing_time_ms=15.7,
            items_processed=200,
            conflicts_resolved=3,
        )

        async def read_fields() -> dict:
            """Async function to read all fields."""
            # Simulate async work
            await asyncio.sleep(0.001)

            return {
                "result": output.result,
                "reduction_type": output.reduction_type,
                "processing_time_ms": output.processing_time_ms,
                "items_processed": output.items_processed,
                "conflicts_resolved": output.conflicts_resolved,
            }

        # Launch 20 concurrent async tasks
        tasks = [read_fields() for _ in range(20)]
        results = await asyncio.gather(*tasks)

        # Validate all tasks succeeded
        assert len(results) == 20
        # Validate data consistency
        for result in results:
            assert result["result"] == 999
            assert result["reduction_type"] == EnumReductionType.FOLD
            assert result["processing_time_ms"] == 15.7
            assert result["items_processed"] == 200
            assert result["conflicts_resolved"] == 3

    @pytest.mark.asyncio
    async def test_async_serialization(self):
        """Test that serialization works correctly in async contexts.

        Validates that model serialization (dict/JSON) is safe to call from
        async functions without blocking the event loop."""
        output = ModelReducerOutput[str](
            result="completed",
            operation_id=uuid4(),
            reduction_type=EnumReductionType.ACCUMULATE,
            processing_time_ms=8.3,
            items_processed=50,
        )

        async def serialize_async() -> tuple:
            """Async serialization operation."""
            await asyncio.sleep(0.001)  # Simulate async work
            dict_result = output.model_dump()
            json_result = output.model_dump_json()
            return (dict_result, json_result)

        # Run multiple serializations concurrently
        tasks = [serialize_async() for _ in range(15)]
        results = await asyncio.gather(*tasks)

        # Validate all succeeded
        assert len(results) == 15
        # Validate consistency
        for dict_result, json_result in results:
            assert dict_result["result"] == "completed"
            assert "accumulate" in json_result.lower()

    @pytest.mark.asyncio
    async def test_async_deserialization(self):
        """Test async-safe deserialization from dict and JSON.

        Validates that model_validate and model_validate_json work correctly
        in async contexts without blocking or coroutine conflicts."""

        async def create_and_serialize() -> str:
            """Create instance and serialize to JSON."""
            output = ModelReducerOutput[int](
                result=42,
                operation_id=uuid4(),
                reduction_type=EnumReductionType.FOLD,
                processing_time_ms=10.0,
                items_processed=5,
            )
            await asyncio.sleep(0.001)
            return output.model_dump_json()

        async def deserialize(json_str: str) -> ModelReducerOutput[int]:
            """Deserialize from JSON."""
            await asyncio.sleep(0.001)
            return ModelReducerOutput[int].model_validate_json(json_str)

        # Create and serialize
        json_str = await create_and_serialize()

        # Deserialize concurrently
        tasks = [deserialize(json_str) for _ in range(10)]
        results = await asyncio.gather(*tasks)

        # Validate all deserializations succeeded
        assert len(results) == 10
        for instance in results:
            assert instance.result == 42
            assert instance.reduction_type == EnumReductionType.FOLD
            assert instance.items_processed == 5

    @pytest.mark.asyncio
    async def test_mixed_sync_async_access(self):
        """Test that instance can be accessed from both sync and async contexts.

        Validates that the model is safe to use in mixed synchronous and
        asynchronous code, which is common in production systems."""
        output = ModelReducerOutput[dict](
            result={"total": 500, "average": 50.0},
            operation_id=uuid4(),
            reduction_type=EnumReductionType.AGGREGATE,
            processing_time_ms=15.3,
            items_processed=10,
        )

        # Sync access
        sync_result = output.result
        sync_type = output.reduction_type

        async def async_access() -> tuple:
            """Async access to same instance."""
            await asyncio.sleep(0.001)
            return (output.result, output.reduction_type)

        # Run async access multiple times
        tasks = [async_access() for _ in range(10)]
        async_results = await asyncio.gather(*tasks)

        # Validate consistency between sync and async access
        assert sync_result == {"total": 500, "average": 50.0}
        assert sync_type == EnumReductionType.AGGREGATE
        for result, reduction_type in async_results:
            assert result == sync_result
            assert reduction_type == sync_type


@pytest.mark.unit
class TestModelReducerOutputUUIDFormatPreservation:
    """Test UUID format preservation through serialization.

    Validates that UUID fields maintain correct format and type through
    serialization/deserialization cycles, as required by distributed systems
    and event-driven architectures.
    """

    def test_operation_id_uuid_format_in_dict(self):
        """Test that operation_id preserves UUID format in dict serialization.

        Validates that UUID objects are correctly represented in dictionary
        form and can be reconstructed without format loss."""
        test_uuid = uuid4()

        output = ModelReducerOutput[int](
            result=42,
            operation_id=test_uuid,
            reduction_type=EnumReductionType.FOLD,
            processing_time_ms=10.0,
            items_processed=5,
        )

        # Serialize to dict
        data_dict = output.model_dump()

        # UUID should be preserved as UUID object in dict
        assert isinstance(data_dict["operation_id"], UUID)
        assert data_dict["operation_id"] == test_uuid
        assert str(data_dict["operation_id"]) == str(test_uuid)

    def test_operation_id_uuid_format_in_json(self):
        """Test that operation_id preserves UUID format in JSON serialization.

        Validates that UUID objects are correctly serialized to string format
        in JSON and maintain standard UUID string representation."""
        test_uuid = uuid4()

        output = ModelReducerOutput[int](
            result=42,
            operation_id=test_uuid,
            reduction_type=EnumReductionType.FOLD,
            processing_time_ms=10.0,
            items_processed=5,
        )

        # Serialize to JSON
        json_str = output.model_dump_json()

        # UUID should be serialized as string in JSON
        assert str(test_uuid) in json_str
        # Validate standard UUID format (8-4-4-4-12 hex digits)
        uuid_str = str(test_uuid)
        assert len(uuid_str) == 36
        assert uuid_str.count("-") == 4

    def test_uuid_roundtrip_preservation(self):
        """Test UUID format preservation through complete roundtrip.

        Validates that UUID objects survive dict→JSON→dict→model cycles
        without format corruption or type loss."""
        original_uuid = uuid4()

        # Create original instance
        original = ModelReducerOutput[int](
            result=42,
            operation_id=original_uuid,
            reduction_type=EnumReductionType.FOLD,
            processing_time_ms=10.0,
            items_processed=5,
        )

        # Roundtrip through dict
        dict_data = original.model_dump()
        from_dict = ModelReducerOutput[int].model_validate(dict_data)
        assert isinstance(from_dict.operation_id, UUID)
        assert from_dict.operation_id == original_uuid

        # Roundtrip through JSON
        json_str = original.model_dump_json()
        from_json = ModelReducerOutput[int].model_validate_json(json_str)
        assert isinstance(from_json.operation_id, UUID)
        assert from_json.operation_id == original_uuid

    def test_uuid_string_input_conversion(self):
        """Test that UUID strings are correctly converted to UUID objects.

        Validates that the model accepts UUID strings and converts them to
        proper UUID objects during validation."""
        uuid_str = str(uuid4())

        output = ModelReducerOutput[int](
            result=42,
            operation_id=uuid_str,  # type: ignore[arg-type]
            reduction_type=EnumReductionType.FOLD,
            processing_time_ms=10.0,
            items_processed=5,
        )

        # Should be converted to UUID object
        assert isinstance(output.operation_id, UUID)
        assert str(output.operation_id) == uuid_str

    def test_intent_uuid_preservation(self):
        """Test that UUID fields in ModelIntent are preserved.

        Validates that intent_id UUIDs in the intents tuple maintain correct
        format through model_copy (Protocol-based typing doesn't support JSON deserialization)."""
        intent_id = uuid4()
        intent = ModelIntent(
            intent_id=intent_id,
            intent_type="log_event",
            target="metrics_service",
            payload=ModelPayloadLogEvent(
                level="INFO",
                message="Test message",
            ),
        )

        output = ModelReducerOutput[int](
            result=42,
            operation_id=uuid4(),
            reduction_type=EnumReductionType.FOLD,
            processing_time_ms=10.0,
            items_processed=5,
            intents=(intent,),
        )

        # Roundtrip through model_copy (Protocol-based payloads don't support JSON deserialization)
        restored = output.model_copy()

        # Intent ID should be preserved
        assert len(restored.intents) == 1
        assert isinstance(restored.intents[0].intent_id, UUID)
        assert restored.intents[0].intent_id == intent_id

    def test_metadata_correlation_id_preservation(self):
        """Test that metadata correlation_id (string) is preserved.

        Validates that correlation IDs in metadata maintain their format
        through serialization, supporting distributed tracing systems."""
        correlation_id = f"corr-{uuid4()}"

        metadata = ModelReducerMetadata(
            source="test_source",
            correlation_id=correlation_id,
        )

        output = ModelReducerOutput[int](
            result=42,
            operation_id=uuid4(),
            reduction_type=EnumReductionType.FOLD,
            processing_time_ms=10.0,
            items_processed=5,
            metadata=metadata,
        )

        # Roundtrip through JSON
        json_str = output.model_dump_json()
        restored = ModelReducerOutput[int].model_validate_json(json_str)

        # Correlation ID should be preserved exactly
        assert restored.metadata.correlation_id == correlation_id
        assert correlation_id in json_str

    def test_metadata_uuid_fields_preservation(self):
        """Test that metadata UUID fields (partition_id, window_id) are preserved.

        Validates that UUID fields in nested metadata objects maintain correct
        format through serialization cycles."""
        partition_id = uuid4()
        window_id = uuid4()

        metadata = ModelReducerMetadata(
            source="event_stream",
            partition_id=partition_id,
            window_id=window_id,
        )

        output = ModelReducerOutput[int](
            result=42,
            operation_id=uuid4(),
            reduction_type=EnumReductionType.AGGREGATE,
            processing_time_ms=15.0,
            items_processed=100,
            metadata=metadata,
        )

        # Roundtrip through dict
        dict_data = output.model_dump()
        restored = ModelReducerOutput[int].model_validate(dict_data)

        # UUIDs should be preserved
        assert isinstance(restored.metadata.partition_id, UUID)
        assert isinstance(restored.metadata.window_id, UUID)
        assert restored.metadata.partition_id == partition_id
        assert restored.metadata.window_id == window_id
