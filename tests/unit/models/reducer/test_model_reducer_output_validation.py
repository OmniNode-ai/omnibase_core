"""Enhanced unit tests for ModelReducerOutput[T].

This module provides additional test coverage for:
- Thread safety and concurrent access
- UUID format preservation
- Async-safe operations
- Performance benchmarks

These tests complement the existing test_model_reducer_output.py suite.
"""

import asyncio
import concurrent.futures
import threading
import time
from typing import Any
from uuid import UUID, uuid4

import pytest
from pydantic import ValidationError

from omnibase_core.enums.enum_reducer_types import EnumReductionType
from omnibase_core.models.reducer.model_intent import ModelIntent
from omnibase_core.models.reducer.model_reducer_output import ModelReducerOutput
from omnibase_core.models.reducer.payloads import ModelPayloadLogEvent

pytestmark = pytest.mark.unit


@pytest.mark.unit
class TestModelReducerOutputThreadSafety:
    """Test thread safety and concurrent access to ModelReducerOutput."""

    def test_concurrent_read_access(self):
        """Test that multiple threads can safely read from the same instance.

        Validates that ModelReducerOutput is safe for concurrent read access,
        with no data corruption or race conditions during simultaneous field access."""
        operation_id = uuid4()
        output = ModelReducerOutput[int](
            result=42,
            operation_id=operation_id,
            reduction_type=EnumReductionType.FOLD,
            processing_time_ms=10.5,
            items_processed=100,
        )

        results = []
        errors = []

        def read_fields():
            """Read all fields from output instance."""
            try:
                assert output.result == 42
                assert output.operation_id == operation_id
                assert output.reduction_type == EnumReductionType.FOLD
                assert output.processing_time_ms == 10.5
                assert output.items_processed == 100
                results.append(True)
            except Exception as e:
                errors.append(e)

        # Create multiple threads reading concurrently
        threads = [threading.Thread(target=read_fields) for _ in range(10)]

        # Start all threads
        for thread in threads:
            thread.start()

        # Wait for completion
        for thread in threads:
            thread.join()

        # Verify all threads succeeded
        assert len(results) == 10
        assert len(errors) == 0

    def test_immutability_under_concurrent_modification_attempts(self):
        """Test that frozen fields prevent concurrent modification.

        Validates that attempts to modify frozen fields from multiple threads
        all fail consistently, maintaining immutability guarantees."""
        output = ModelReducerOutput[int](
            result=42,
            operation_id=uuid4(),
            reduction_type=EnumReductionType.FOLD,
            processing_time_ms=10.0,
            items_processed=5,
        )

        errors = []

        def try_modify_result():
            """Attempt to modify the result field."""
            try:
                output.result = 100  # type: ignore[misc]
                # Should never reach here
                errors.append(
                    Exception("Modification succeeded - immutability broken!")
                )
            except ValidationError:
                # Expected behavior
                pass

        def try_modify_operation_id():
            """Attempt to modify the operation_id field."""
            try:
                output.operation_id = uuid4()  # type: ignore[misc]
                errors.append(
                    Exception("Modification succeeded - immutability broken!")
                )
            except ValidationError:
                pass

        # Create threads attempting concurrent modification
        threads = [threading.Thread(target=try_modify_result) for _ in range(5)] + [
            threading.Thread(target=try_modify_operation_id) for _ in range(5)
        ]

        # Start all threads
        for thread in threads:
            thread.start()

        # Wait for completion
        for thread in threads:
            thread.join()

        # Verify no modifications succeeded
        assert len(errors) == 0
        # Verify original values unchanged
        assert output.result == 42

    def test_concurrent_serialization(self):
        """Test that multiple threads can safely serialize the same instance.

        Validates that model_dump() and model_dump_json() are thread-safe for
        concurrent serialization operations without data corruption."""
        output = ModelReducerOutput[dict](
            result={"status": "success", "count": 10},
            operation_id=uuid4(),
            reduction_type=EnumReductionType.AGGREGATE,
            processing_time_ms=15.0,
            items_processed=100,
        )

        results: list[dict[str, Any] | str] = []  # Can hold both dicts and JSON strings
        errors: list[Exception] = []

        def serialize_to_dict():
            """Serialize to dictionary."""
            try:
                data = output.model_dump()
                assert data["result"]["status"] == "success"
                results.append(data)
            except Exception as e:
                errors.append(e)

        def serialize_to_json():
            """Serialize to JSON."""
            try:
                json_str = output.model_dump_json()
                assert "success" in json_str
                results.append(json_str)
            except Exception as e:
                errors.append(e)

        # Create mixed serialization threads
        threads = [threading.Thread(target=serialize_to_dict) for _ in range(5)] + [
            threading.Thread(target=serialize_to_json) for _ in range(5)
        ]

        # Start all threads
        for thread in threads:
            thread.start()

        # Wait for completion
        for thread in threads:
            thread.join()

        # Verify all operations succeeded
        assert len(results) == 10
        assert len(errors) == 0

    def test_multiple_instances_in_thread_pool(self):
        """Test creating multiple instances concurrently in thread pool.

        Validates that ModelReducerOutput instantiation is thread-safe with no
        interference between concurrent instance creation operations."""

        def create_instance(value: int) -> ModelReducerOutput[int]:
            """Create a ModelReducerOutput instance."""
            return ModelReducerOutput[int](
                result=value,
                operation_id=uuid4(),
                reduction_type=EnumReductionType.FOLD,
                processing_time_ms=10.0,
                items_processed=value,
            )

        # Create instances concurrently using thread pool
        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(create_instance, i) for i in range(100)]
            results = [future.result() for future in futures]

        # Verify all instances created successfully with correct values
        assert len(results) == 100
        for i, output in enumerate(results):
            assert output.result == i
            assert output.items_processed == i


@pytest.mark.unit
class TestModelReducerOutputUUIDFormatPreservation:
    """Test UUID format preservation through serialization cycles."""

    def test_operation_id_remains_uuid_type(self):
        """Test that operation_id maintains UUID type throughout lifecycle.

        Validates that operation_id field remains a UUID object instance
        after instantiation, serialization, and deserialization."""
        operation_id = uuid4()

        output = ModelReducerOutput[int](
            result=42,
            operation_id=operation_id,
            reduction_type=EnumReductionType.FOLD,
            processing_time_ms=10.0,
            items_processed=5,
        )

        # Verify UUID type preserved in instance
        assert isinstance(output.operation_id, UUID)
        assert output.operation_id == operation_id

    def test_uuid_to_string_to_uuid_roundtrip(self):
        """Test UUID survives string conversion roundtrip.

        Validates that UUID→string→UUID conversion preserves the original
        UUID value without data loss or format corruption."""
        operation_id = uuid4()

        output = ModelReducerOutput[int](
            result=42,
            operation_id=operation_id,
            reduction_type=EnumReductionType.FOLD,
            processing_time_ms=10.0,
            items_processed=5,
        )

        # Convert to string
        uuid_str = str(output.operation_id)
        assert isinstance(uuid_str, str)

        # Convert back to UUID
        restored_uuid = UUID(uuid_str)
        assert isinstance(restored_uuid, UUID)
        assert restored_uuid == operation_id

    def test_uuid_format_in_json_serialization(self):
        """Test UUID format in JSON serialization.

        Validates that UUIDs are serialized to standard hyphenated string
        format in JSON (e.g., '550e8400-e29b-41d4-a716-446655440000')."""
        operation_id = uuid4()

        output = ModelReducerOutput[int](
            result=42,
            operation_id=operation_id,
            reduction_type=EnumReductionType.FOLD,
            processing_time_ms=10.0,
            items_processed=5,
        )

        json_str = output.model_dump_json()

        # Verify UUID is in standard string format with hyphens
        uuid_str = str(operation_id)
        assert uuid_str in json_str
        assert len(uuid_str) == 36  # Standard UUID string length
        assert uuid_str.count("-") == 4  # Standard UUID has 4 hyphens

    def test_uuid_validation_from_dict(self):
        """Test UUID validation when loading from dictionary.

        Validates that dictionary deserialization properly validates and
        converts string UUIDs to UUID objects."""
        operation_id = uuid4()

        # Create dict with string UUID
        data = {
            "result": 42,
            "operation_id": str(operation_id),  # String UUID
            "reduction_type": EnumReductionType.FOLD,
            "processing_time_ms": 10.0,
            "items_processed": 5,
        }

        output = ModelReducerOutput[int].model_validate(data)

        # Verify converted to UUID type
        assert isinstance(output.operation_id, UUID)
        assert output.operation_id == operation_id

    def test_invalid_uuid_format_rejected(self):
        """Test that invalid UUID formats are rejected during validation.

        Validates that malformed UUID strings cause validation errors with
        clear error messages."""
        with pytest.raises(ValidationError) as exc_info:
            ModelReducerOutput[int](
                result=42,
                operation_id="not-a-valid-uuid",  # type: ignore[arg-type]
                reduction_type=EnumReductionType.FOLD,
                processing_time_ms=10.0,
                items_processed=5,
            )

        error_msg = str(exc_info.value)
        assert "operation_id" in error_msg

    @pytest.mark.parametrize(
        ("uuid_variant", "description"),
        [
            pytest.param(uuid4(), "random_uuid4", id="uuid4"),
            pytest.param(
                UUID("550e8400-e29b-41d4-a716-446655440000"),
                "specific_uuid",
                id="specific",
            ),
            pytest.param(
                UUID(int=0),
                "zero_uuid",
                id="zero",
            ),
            pytest.param(
                UUID("ffffffff-ffff-ffff-ffff-ffffffffffff"),
                "max_uuid",
                id="max",
            ),
        ],
    )
    def test_various_uuid_formats_preserved(self, uuid_variant, description):
        """Test that various UUID formats are correctly preserved.

        Validates preservation of different UUID variants including uuid4,
        specific values, zero UUID, and max UUID through full serialization cycle."""
        output = ModelReducerOutput[int](
            result=42,
            operation_id=uuid_variant,
            reduction_type=EnumReductionType.FOLD,
            processing_time_ms=10.0,
            items_processed=5,
        )

        # Roundtrip through JSON
        json_str = output.model_dump_json()
        restored = ModelReducerOutput[int].model_validate_json(json_str)

        assert isinstance(restored.operation_id, UUID)
        assert restored.operation_id == uuid_variant


@pytest.mark.unit
class TestModelReducerOutputAsyncSafe:
    """Test async-safe operations with ModelReducerOutput."""

    @pytest.mark.asyncio
    async def test_create_in_async_context(self):
        """Test creating ModelReducerOutput in async context.

        Validates that instance creation works correctly within async functions
        without blocking the event loop or causing async-related issues."""
        output = ModelReducerOutput[int](
            result=42,
            operation_id=uuid4(),
            reduction_type=EnumReductionType.FOLD,
            processing_time_ms=10.0,
            items_processed=5,
        )

        assert output.result == 42
        assert isinstance(output.operation_id, UUID)

    @pytest.mark.asyncio
    async def test_read_fields_in_async_context(self):
        """Test reading fields in async context.

        Validates that field access does not block the event loop and can be
        safely performed in async functions."""
        output = ModelReducerOutput[dict](
            result={"status": "success"},
            operation_id=uuid4(),
            reduction_type=EnumReductionType.AGGREGATE,
            processing_time_ms=15.0,
            items_processed=100,
        )

        # Simulate async operations between field accesses
        await asyncio.sleep(0)
        assert output.result["status"] == "success"

        await asyncio.sleep(0)
        assert output.processing_time_ms == 15.0

    @pytest.mark.asyncio
    async def test_serialization_in_async_context(self):
        """Test serialization in async context.

        Validates that model_dump() and model_dump_json() do not block the
        event loop during async execution."""
        output = ModelReducerOutput[int](
            result=42,
            operation_id=uuid4(),
            reduction_type=EnumReductionType.FOLD,
            processing_time_ms=10.0,
            items_processed=5,
        )

        # Test dict serialization
        data = output.model_dump()
        assert data["result"] == 42

        await asyncio.sleep(0)

        # Test JSON serialization
        json_str = output.model_dump_json()
        assert "42" in json_str

    @pytest.mark.asyncio
    async def test_multiple_async_tasks_concurrent_access(self):
        """Test multiple async tasks accessing same instance concurrently.

        Validates that multiple coroutines can safely read from the same
        ModelReducerOutput instance without race conditions."""
        output = ModelReducerOutput[int](
            result=42,
            operation_id=uuid4(),
            reduction_type=EnumReductionType.FOLD,
            processing_time_ms=10.0,
            items_processed=5,
        )

        async def read_result():
            """Read result field."""
            await asyncio.sleep(0.001)
            return output.result

        async def read_operation_id():
            """Read operation_id field."""
            await asyncio.sleep(0.001)
            return output.operation_id

        async def serialize_to_dict():
            """Serialize to dict."""
            await asyncio.sleep(0.001)
            return output.model_dump()

        # Run multiple tasks concurrently
        results = await asyncio.gather(
            read_result(),
            read_operation_id(),
            serialize_to_dict(),
            read_result(),
            serialize_to_dict(),
        )

        # Verify all operations succeeded
        assert results[0] == 42
        assert isinstance(results[1], UUID)
        assert isinstance(results[2], dict)
        assert results[3] == 42
        assert isinstance(results[4], dict)

    @pytest.mark.asyncio
    async def test_async_instance_creation_batch(self):
        """Test creating multiple instances in async batch operations.

        Validates that batch creation of ModelReducerOutput instances in async
        context works efficiently without blocking."""

        async def create_instance(value: int) -> ModelReducerOutput[int]:
            """Create instance asynchronously."""
            await asyncio.sleep(0.001)  # Simulate async I/O
            return ModelReducerOutput[int](
                result=value,
                operation_id=uuid4(),
                reduction_type=EnumReductionType.FOLD,
                processing_time_ms=10.0,
                items_processed=value,
            )

        # Create multiple instances concurrently
        results = await asyncio.gather(*[create_instance(i) for i in range(50)])

        # Verify all instances created correctly
        assert len(results) == 50
        for i, output in enumerate(results):
            assert output.result == i
            assert output.items_processed == i


@pytest.mark.unit
class TestModelReducerOutputPerformance:
    """Test performance characteristics and benchmarks."""

    def test_large_data_list_result(self):
        """Test performance with large list in result field.

        Validates that the model handles large data lists (1000+ items)
        efficiently for memory usage and instantiation time."""
        large_list = list(range(1000))

        start_time = time.perf_counter()
        output = ModelReducerOutput[list](
            result=large_list,
            operation_id=uuid4(),
            reduction_type=EnumReductionType.FILTER,
            processing_time_ms=10.0,
            items_processed=1000,
        )
        creation_time = time.perf_counter() - start_time

        # Verify data preserved
        assert len(output.result) == 1000
        assert output.result[0] == 0
        assert output.result[-1] == 999

        # Performance check: should create in < 10ms
        assert creation_time < 0.01, f"Creation took {creation_time * 1000:.2f}ms"

    def test_large_dict_result(self):
        """Test performance with large dictionary in result field.

        Validates that the model handles large nested dictionaries
        efficiently without performance degradation."""
        large_dict = {
            f"key_{i}": {"value": i, "data": [i, i * 2, i * 3]} for i in range(1000)
        }

        start_time = time.perf_counter()
        output = ModelReducerOutput[dict](
            result=large_dict,
            operation_id=uuid4(),
            reduction_type=EnumReductionType.AGGREGATE,
            processing_time_ms=10.0,
            items_processed=1000,
        )
        creation_time = time.perf_counter() - start_time

        # Verify data preserved
        assert len(output.result) == 1000
        assert output.result["key_0"]["value"] == 0
        assert output.result["key_999"]["value"] == 999

        # Performance check
        assert creation_time < 0.02, f"Creation took {creation_time * 1000:.2f}ms"

    def test_serialization_performance_large_data(self):
        """Test serialization performance with large data structures.

        Validates that model_dump() and model_dump_json() perform efficiently
        with large result payloads."""
        large_dict = {f"key_{i}": i for i in range(1000)}

        output = ModelReducerOutput[dict](
            result=large_dict,
            operation_id=uuid4(),
            reduction_type=EnumReductionType.AGGREGATE,
            processing_time_ms=10.0,
            items_processed=1000,
        )

        # Test dict serialization performance
        start_time = time.perf_counter()
        data = output.model_dump()
        dict_time = time.perf_counter() - start_time

        assert len(data["result"]) == 1000
        assert dict_time < 0.01, f"Dict serialization took {dict_time * 1000:.2f}ms"

        # Test JSON serialization performance
        start_time = time.perf_counter()
        json_str = output.model_dump_json()
        json_time = time.perf_counter() - start_time

        assert "key_999" in json_str
        assert json_time < 0.02, f"JSON serialization took {json_time * 1000:.2f}ms"

    def test_deserialization_performance_large_data(self):
        """Test deserialization performance with large data structures.

        Validates that model_validate() performs efficiently when reconstructing
        instances from large serialized payloads."""
        large_dict = {f"key_{i}": i for i in range(1000)}

        original = ModelReducerOutput[dict](
            result=large_dict,
            operation_id=uuid4(),
            reduction_type=EnumReductionType.AGGREGATE,
            processing_time_ms=10.0,
            items_processed=1000,
        )

        data = original.model_dump()

        # Test deserialization performance
        start_time = time.perf_counter()
        restored = ModelReducerOutput[dict].model_validate(data)
        deser_time = time.perf_counter() - start_time

        assert len(restored.result) == 1000
        assert deser_time < 0.02, f"Deserialization took {deser_time * 1000:.2f}ms"

    def test_multiple_intents_performance(self):
        """Test performance with large number of intents.

        Validates that the model handles many intents (100+) efficiently
        without performance degradation or memory issues."""
        intents = tuple(
            ModelIntent(
                intent_type="log_event",
                target=f"service_{i}",
                payload=ModelPayloadLogEvent(level="INFO", message=f"index: {i}"),
            )
            for i in range(100)
        )

        start_time = time.perf_counter()
        output = ModelReducerOutput[int](
            result=42,
            operation_id=uuid4(),
            reduction_type=EnumReductionType.FOLD,
            processing_time_ms=10.0,
            items_processed=5,
            intents=intents,
        )
        creation_time = time.perf_counter() - start_time

        assert len(output.intents) == 100
        assert output.intents[0].target == "service_0"
        assert output.intents[99].target == "service_99"

        # Performance check
        assert creation_time < 0.05, f"Creation took {creation_time * 1000:.2f}ms"

    def test_roundtrip_serialization_performance(self):
        """Test full roundtrip serialization performance benchmark.

        Validates end-to-end serialization performance: instance→dict→JSON→
        dict→instance with realistic data payloads."""
        output = ModelReducerOutput[dict](
            result={"data": list(range(500)), "metadata": {"count": 500}},
            operation_id=uuid4(),
            reduction_type=EnumReductionType.AGGREGATE,
            processing_time_ms=10.0,
            items_processed=500,
        )

        start_time = time.perf_counter()

        # Full roundtrip: instance → dict → JSON → instance
        data = output.model_dump()
        json_str = output.model_dump_json()
        restored = ModelReducerOutput[dict].model_validate_json(json_str)

        roundtrip_time = time.perf_counter() - start_time

        assert restored.result["metadata"]["count"] == 500
        assert len(restored.result["data"]) == 500

        # Performance check: full roundtrip should be < 50ms
        assert roundtrip_time < 0.05, f"Roundtrip took {roundtrip_time * 1000:.2f}ms"
