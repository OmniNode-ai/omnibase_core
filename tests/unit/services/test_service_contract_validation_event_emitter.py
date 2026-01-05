# SPDX-FileCopyrightText: 2025 OmniNode Team <info@omninode.ai>
#
# SPDX-License-Identifier: Apache-2.0
"""Unit tests for ServiceContractValidationEventEmitter.

Tests cover:
- Memory sink event storage
- File sink JSONL format writing
- Multiple destination event routing
- Correlation ID propagation
- Flush and close behavior
- Event retrieval methods
- Sink statistics accuracy
- Error handling scenarios

Related:
    - OMN-1151: Event emission for contract validation
"""

from __future__ import annotations

import json
import tempfile
from pathlib import Path
from uuid import uuid4

import pytest

from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.enums.enum_event_sink_type import EnumEventSinkType
from omnibase_core.errors import ModelOnexError
from omnibase_core.models.events.contract_validation import (
    ModelContractMergeCompletedEvent,
    ModelContractMergeStartedEvent,
    ModelContractValidationContext,
    ModelContractValidationFailedEvent,
    ModelContractValidationPassedEvent,
    ModelContractValidationStartedEvent,
)
from omnibase_core.models.validation.model_event_destination import (
    ModelEventDestination,
)
from omnibase_core.services.service_contract_validation_event_emitter import (
    ServiceContractValidationEventEmitter,
    SinkFile,
    SinkMemory,
)

# =============================================================================
# Memory Sink Tests
# =============================================================================


@pytest.mark.unit
class TestSinkMemory:
    """Tests for the in-memory event sink."""

    @pytest.mark.asyncio
    async def test_write_stores_event(self) -> None:
        """Test that write stores event in memory."""
        sink = SinkMemory(name="test-sink")
        run_id = uuid4()
        event = ModelContractValidationStartedEvent(
            contract_name="test-contract",
            run_id=run_id,
            context=ModelContractValidationContext(),
        )

        await sink.write(event)

        events = sink.get_events()
        assert len(events) == 1
        assert events[0].contract_name == "test-contract"
        assert events[0].run_id == run_id

    @pytest.mark.asyncio
    async def test_write_multiple_events(self) -> None:
        """Test storing multiple events in sequence."""
        sink = SinkMemory(name="multi-test")
        run_id = uuid4()

        event1 = ModelContractValidationStartedEvent(
            contract_name="contract-1",
            run_id=run_id,
            context=ModelContractValidationContext(),
        )
        event2 = ModelContractValidationPassedEvent(
            contract_name="contract-1",
            run_id=run_id,
            duration_ms=150,
        )

        await sink.write(event1)
        await sink.write(event2)

        events = sink.get_events()
        assert len(events) == 2
        assert events[0].contract_name == "contract-1"
        assert isinstance(events[0], ModelContractValidationStartedEvent)
        assert isinstance(events[1], ModelContractValidationPassedEvent)

    @pytest.mark.asyncio
    async def test_get_events_returns_copy(self) -> None:
        """Test that get_events returns a copy, not the internal list."""
        sink = SinkMemory(name="copy-test")
        run_id = uuid4()
        event = ModelContractValidationStartedEvent(
            contract_name="test",
            run_id=run_id,
            context=ModelContractValidationContext(),
        )

        await sink.write(event)

        events1 = sink.get_events()
        events2 = sink.get_events()

        # Should be different list objects
        assert events1 is not events2
        # But same content
        assert events1 == events2

    @pytest.mark.asyncio
    async def test_clear_removes_all_events(self) -> None:
        """Test that clear removes all stored events."""
        sink = SinkMemory(name="clear-test")
        run_id = uuid4()
        event = ModelContractValidationStartedEvent(
            contract_name="test",
            run_id=run_id,
            context=ModelContractValidationContext(),
        )

        await sink.write(event)
        assert sink.event_count == 1

        sink.clear()

        assert sink.event_count == 0
        assert len(sink.get_events()) == 0

    @pytest.mark.asyncio
    async def test_flush_is_noop(self) -> None:
        """Test that flush is a no-op for memory sink."""
        sink = SinkMemory(name="flush-test")
        run_id = uuid4()
        event = ModelContractValidationStartedEvent(
            contract_name="test",
            run_id=run_id,
            context=ModelContractValidationContext(),
        )

        await sink.write(event)
        await sink.flush()

        # Events should still be present after flush
        assert sink.event_count == 1

    @pytest.mark.asyncio
    async def test_close_prevents_further_writes(self) -> None:
        """Test that close prevents further writes."""
        sink = SinkMemory(name="close-test")
        run_id = uuid4()
        event = ModelContractValidationStartedEvent(
            contract_name="test",
            run_id=run_id,
            context=ModelContractValidationContext(),
        )

        await sink.close()

        with pytest.raises(ModelOnexError) as exc_info:
            await sink.write(event)

        assert exc_info.value.error_code == EnumCoreErrorCode.OPERATION_FAILED
        assert "closed" in exc_info.value.message.lower()

    def test_sink_type_is_memory(self) -> None:
        """Test that sink_type returns correct value."""
        sink = SinkMemory(name="type-test")
        assert sink.sink_type == EnumEventSinkType.MEMORY.value

    def test_is_ready_before_close(self) -> None:
        """Test that is_ready is True before close."""
        sink = SinkMemory(name="ready-test")
        assert sink.is_ready is True

    @pytest.mark.asyncio
    async def test_is_ready_after_close(self) -> None:
        """Test that is_ready is False after close."""
        sink = SinkMemory(name="ready-close-test")
        await sink.close()
        assert sink.is_ready is False

    @pytest.mark.asyncio
    async def test_event_count_increments(self) -> None:
        """Test that event_count tracks events correctly."""
        sink = SinkMemory(name="count-test")
        assert sink.event_count == 0

        for i in range(5):
            event = ModelContractValidationStartedEvent(
                contract_name=f"contract-{i}",
                run_id=uuid4(),
                context=ModelContractValidationContext(),
            )
            await sink.write(event)

        assert sink.event_count == 5


# =============================================================================
# File Sink Tests
# =============================================================================


@pytest.mark.unit
class TestSinkFile:
    """Tests for the file-based event sink."""

    @pytest.mark.asyncio
    async def test_write_and_flush_creates_file(self) -> None:
        """Test that write and flush creates file with JSONL content."""
        with tempfile.TemporaryDirectory() as tmpdir:
            file_path = Path(tmpdir) / "events.jsonl"
            sink = SinkFile(name="file-test", file_path=file_path, buffer_size=100)

            run_id = uuid4()
            event = ModelContractValidationStartedEvent(
                contract_name="test-contract",
                run_id=run_id,
                context=ModelContractValidationContext(),
            )

            await sink.write(event)
            await sink.flush()

            assert file_path.exists()
            content = file_path.read_text()
            lines = content.strip().split("\n")
            assert len(lines) == 1

            data = json.loads(lines[0])
            assert data["contract_name"] == "test-contract"
            assert data["run_id"] == str(run_id)

    @pytest.mark.asyncio
    async def test_writes_jsonl_format(self) -> None:
        """Test that multiple events produce JSONL format (one per line)."""
        with tempfile.TemporaryDirectory() as tmpdir:
            file_path = Path(tmpdir) / "multi.jsonl"
            sink = SinkFile(name="jsonl-test", file_path=file_path, buffer_size=100)

            run_id = uuid4()
            events = [
                ModelContractValidationStartedEvent(
                    contract_name="contract",
                    run_id=run_id,
                    context=ModelContractValidationContext(),
                ),
                ModelContractValidationPassedEvent(
                    contract_name="contract",
                    run_id=run_id,
                    duration_ms=100,
                ),
            ]

            for event in events:
                await sink.write(event)
            await sink.flush()

            content = file_path.read_text()
            lines = content.strip().split("\n")
            assert len(lines) == 2

            # Each line should be valid JSON
            for line in lines:
                data = json.loads(line)
                assert "contract_name" in data

    @pytest.mark.asyncio
    async def test_auto_flush_on_buffer_full(self) -> None:
        """Test that buffer is auto-flushed when full."""
        with tempfile.TemporaryDirectory() as tmpdir:
            file_path = Path(tmpdir) / "auto-flush.jsonl"
            sink = SinkFile(name="buffer-test", file_path=file_path, buffer_size=3)

            # Write 4 events (buffer_size=3, so should auto-flush after 3rd)
            for i in range(4):
                event = ModelContractValidationStartedEvent(
                    contract_name=f"contract-{i}",
                    run_id=uuid4(),
                    context=ModelContractValidationContext(),
                )
                await sink.write(event)

            # File should exist without explicit flush (auto-flushed after 3rd)
            assert file_path.exists()

            # Explicitly flush the remaining event
            await sink.flush()

            content = file_path.read_text()
            lines = content.strip().split("\n")
            assert len(lines) == 4

    @pytest.mark.asyncio
    async def test_close_flushes_remaining(self) -> None:
        """Test that close flushes any buffered events."""
        with tempfile.TemporaryDirectory() as tmpdir:
            file_path = Path(tmpdir) / "close-flush.jsonl"
            sink = SinkFile(name="close-test", file_path=file_path, buffer_size=100)

            event = ModelContractValidationStartedEvent(
                contract_name="test",
                run_id=uuid4(),
                context=ModelContractValidationContext(),
            )

            await sink.write(event)
            # Don't call flush, just close
            await sink.close()

            assert file_path.exists()
            content = file_path.read_text()
            assert "test" in content

    @pytest.mark.asyncio
    async def test_close_prevents_further_writes(self) -> None:
        """Test that close prevents further writes."""
        with tempfile.TemporaryDirectory() as tmpdir:
            file_path = Path(tmpdir) / "close-prevent.jsonl"
            sink = SinkFile(name="prevent-test", file_path=file_path)

            await sink.close()

            event = ModelContractValidationStartedEvent(
                contract_name="test",
                run_id=uuid4(),
                context=ModelContractValidationContext(),
            )

            with pytest.raises(ModelOnexError) as exc_info:
                await sink.write(event)

            assert exc_info.value.error_code == EnumCoreErrorCode.OPERATION_FAILED

    def test_sink_type_is_file(self) -> None:
        """Test that sink_type returns correct value."""
        with tempfile.TemporaryDirectory() as tmpdir:
            sink = SinkFile(name="type-test", file_path=Path(tmpdir) / "test.jsonl")
            assert sink.sink_type == EnumEventSinkType.FILE.value

    @pytest.mark.asyncio
    async def test_event_count_tracks_total(self) -> None:
        """Test that event_count tracks total events written."""
        with tempfile.TemporaryDirectory() as tmpdir:
            file_path = Path(tmpdir) / "count.jsonl"
            sink = SinkFile(name="count-test", file_path=file_path)

            for i in range(5):
                event = ModelContractValidationStartedEvent(
                    contract_name=f"contract-{i}",
                    run_id=uuid4(),
                    context=ModelContractValidationContext(),
                )
                await sink.write(event)

            assert sink.event_count == 5

    @pytest.mark.asyncio
    async def test_buffer_count_before_flush(self) -> None:
        """Test that buffer_count tracks unflushed events."""
        with tempfile.TemporaryDirectory() as tmpdir:
            file_path = Path(tmpdir) / "buffer.jsonl"
            sink = SinkFile(
                name="buffer-count-test", file_path=file_path, buffer_size=100
            )

            assert sink.buffer_count == 0

            for i in range(3):
                event = ModelContractValidationStartedEvent(
                    contract_name=f"contract-{i}",
                    run_id=uuid4(),
                    context=ModelContractValidationContext(),
                )
                await sink.write(event)

            assert sink.buffer_count == 3

            await sink.flush()

            assert sink.buffer_count == 0

    @pytest.mark.asyncio
    async def test_creates_parent_directories(self) -> None:
        """Test that flush creates parent directories if needed."""
        with tempfile.TemporaryDirectory() as tmpdir:
            file_path = Path(tmpdir) / "nested" / "dir" / "events.jsonl"
            sink = SinkFile(name="nested-test", file_path=file_path)

            event = ModelContractValidationStartedEvent(
                contract_name="test",
                run_id=uuid4(),
                context=ModelContractValidationContext(),
            )

            await sink.write(event)
            await sink.flush()

            assert file_path.exists()
            assert file_path.parent.exists()


# =============================================================================
# Emitter Service Tests
# =============================================================================


@pytest.mark.unit
class TestServiceContractValidationEventEmitter:
    """Tests for the event emitter service."""

    @pytest.mark.asyncio
    async def test_emit_to_memory_sink(self) -> None:
        """Test emitting events to memory sink."""
        emitter = ServiceContractValidationEventEmitter(
            destinations=[ModelEventDestination.create_memory(name="test")],
        )

        run_id = uuid4()
        event = ModelContractValidationStartedEvent(
            contract_name="test-contract",
            run_id=run_id,
            context=ModelContractValidationContext(),
        )

        await emitter.emit(event)

        events = emitter.get_events("test")
        assert len(events) == 1
        assert events[0].contract_name == "test-contract"

    @pytest.mark.asyncio
    async def test_emit_to_file_sink(self) -> None:
        """Test emitting events to file sink."""
        with tempfile.TemporaryDirectory() as tmpdir:
            file_path = Path(tmpdir) / "events.jsonl"
            emitter = ServiceContractValidationEventEmitter(
                destinations=[
                    ModelEventDestination.create_file(
                        name="file",
                        file_path=str(file_path),
                    )
                ],
            )

            event = ModelContractValidationStartedEvent(
                contract_name="test",
                run_id=uuid4(),
                context=ModelContractValidationContext(),
            )

            await emitter.emit(event)
            await emitter.flush()

            assert file_path.exists()

    @pytest.mark.asyncio
    async def test_emit_to_multiple_destinations(self) -> None:
        """Test that events are emitted to all destinations."""
        with tempfile.TemporaryDirectory() as tmpdir:
            file_path = Path(tmpdir) / "multi.jsonl"
            emitter = ServiceContractValidationEventEmitter(
                destinations=[
                    ModelEventDestination.create_memory(name="memory1"),
                    ModelEventDestination.create_memory(name="memory2"),
                    ModelEventDestination.create_file(
                        name="file", file_path=str(file_path)
                    ),
                ],
            )

            event = ModelContractValidationStartedEvent(
                contract_name="multi-test",
                run_id=uuid4(),
                context=ModelContractValidationContext(),
            )

            await emitter.emit(event)
            await emitter.flush()

            # Check memory sinks
            events1 = emitter.get_events("memory1")
            events2 = emitter.get_events("memory2")
            assert len(events1) == 1
            assert len(events2) == 1

            # Check file sink
            assert file_path.exists()

    @pytest.mark.asyncio
    async def test_correlation_id_propagation(self) -> None:
        """Test that correlation_id is propagated to events without one."""
        correlation_id = uuid4()
        emitter = ServiceContractValidationEventEmitter(
            destinations=[ModelEventDestination.create_memory(name="memory")],
            correlation_id=correlation_id,
        )

        # Event without correlation_id
        event = ModelContractValidationStartedEvent(
            contract_name="test",
            run_id=uuid4(),
            context=ModelContractValidationContext(),
        )
        assert event.correlation_id is None

        await emitter.emit(event)

        events = emitter.get_events("memory")
        assert len(events) == 1
        # Event should now have the emitter's correlation_id
        assert events[0].correlation_id == correlation_id

    @pytest.mark.asyncio
    async def test_correlation_id_not_overwritten(self) -> None:
        """Test that existing correlation_id is not overwritten."""
        emitter_correlation = uuid4()
        event_correlation = uuid4()

        emitter = ServiceContractValidationEventEmitter(
            destinations=[ModelEventDestination.create_memory(name="memory")],
            correlation_id=emitter_correlation,
        )

        # Event with its own correlation_id
        event = ModelContractValidationStartedEvent(
            contract_name="test",
            run_id=uuid4(),
            context=ModelContractValidationContext(),
            correlation_id=event_correlation,
        )

        await emitter.emit(event)

        events = emitter.get_events("memory")
        assert len(events) == 1
        # Event should keep its original correlation_id
        assert events[0].correlation_id == event_correlation

    @pytest.mark.asyncio
    async def test_emit_increments_count(self) -> None:
        """Test that emit_count is incremented on each emit."""
        emitter = ServiceContractValidationEventEmitter(
            destinations=[ModelEventDestination.create_memory()],
        )

        assert emitter.emit_count == 0

        for i in range(3):
            event = ModelContractValidationStartedEvent(
                contract_name=f"test-{i}",
                run_id=uuid4(),
                context=ModelContractValidationContext(),
            )
            await emitter.emit(event)

        assert emitter.emit_count == 3

    @pytest.mark.asyncio
    async def test_last_emit_time_updated(self) -> None:
        """Test that last_emit_time is updated on emit."""
        emitter = ServiceContractValidationEventEmitter(
            destinations=[ModelEventDestination.create_memory()],
        )

        assert emitter.last_emit_time is None

        event = ModelContractValidationStartedEvent(
            contract_name="test",
            run_id=uuid4(),
            context=ModelContractValidationContext(),
        )
        await emitter.emit(event)

        assert emitter.last_emit_time is not None

    @pytest.mark.asyncio
    async def test_flush_flushes_all_sinks(self) -> None:
        """Test that flush flushes all sinks."""
        with tempfile.TemporaryDirectory() as tmpdir:
            file1 = Path(tmpdir) / "file1.jsonl"
            file2 = Path(tmpdir) / "file2.jsonl"
            emitter = ServiceContractValidationEventEmitter(
                destinations=[
                    ModelEventDestination.create_file(name="f1", file_path=str(file1)),
                    ModelEventDestination.create_file(name="f2", file_path=str(file2)),
                ],
            )

            event = ModelContractValidationStartedEvent(
                contract_name="test",
                run_id=uuid4(),
                context=ModelContractValidationContext(),
            )
            await emitter.emit(event)
            await emitter.flush()

            assert file1.exists()
            assert file2.exists()

    @pytest.mark.asyncio
    async def test_close_closes_all_sinks(self) -> None:
        """Test that close closes all sinks."""
        emitter = ServiceContractValidationEventEmitter(
            destinations=[
                ModelEventDestination.create_memory(name="m1"),
                ModelEventDestination.create_memory(name="m2"),
            ],
        )

        await emitter.close()

        # Verify all sinks are marked as not ready
        stats = emitter.get_sink_stats()
        assert stats["m1"]["ready"] is False
        assert stats["m2"]["ready"] is False

    def test_get_events_raises_for_unknown_sink(self) -> None:
        """Test that get_events raises for unknown sink name."""
        emitter = ServiceContractValidationEventEmitter(
            destinations=[ModelEventDestination.create_memory(name="known")],
        )

        with pytest.raises(ModelOnexError) as exc_info:
            emitter.get_events("unknown")

        assert exc_info.value.error_code == EnumCoreErrorCode.NOT_FOUND

    @pytest.mark.asyncio
    async def test_get_events_raises_for_non_memory_sink(self) -> None:
        """Test that get_events raises for non-memory sink."""
        with tempfile.TemporaryDirectory() as tmpdir:
            file_path = Path(tmpdir) / "test.jsonl"
            emitter = ServiceContractValidationEventEmitter(
                destinations=[
                    ModelEventDestination.create_file(
                        name="file-sink", file_path=str(file_path)
                    )
                ],
            )

            with pytest.raises(ModelOnexError) as exc_info:
                emitter.get_events("file-sink")

            assert exc_info.value.error_code == EnumCoreErrorCode.INVALID_OPERATION

    @pytest.mark.asyncio
    async def test_clear_events(self) -> None:
        """Test clearing events from memory sink."""
        emitter = ServiceContractValidationEventEmitter(
            destinations=[ModelEventDestination.create_memory(name="memory")],
        )

        event = ModelContractValidationStartedEvent(
            contract_name="test",
            run_id=uuid4(),
            context=ModelContractValidationContext(),
        )
        await emitter.emit(event)

        assert len(emitter.get_events("memory")) == 1

        emitter.clear_events("memory")

        assert len(emitter.get_events("memory")) == 0

    def test_get_sink_stats(self) -> None:
        """Test get_sink_stats returns correct information."""
        emitter = ServiceContractValidationEventEmitter(
            destinations=[
                ModelEventDestination.create_memory(name="mem"),
            ],
        )

        stats = emitter.get_sink_stats()

        assert "mem" in stats
        assert stats["mem"]["type"] == "memory"
        assert stats["mem"]["ready"] is True
        assert stats["mem"]["event_count"] == 0

    @pytest.mark.asyncio
    async def test_get_sink_stats_with_file_sink(self) -> None:
        """Test get_sink_stats includes buffer_count for file sinks."""
        with tempfile.TemporaryDirectory() as tmpdir:
            file_path = Path(tmpdir) / "test.jsonl"
            emitter = ServiceContractValidationEventEmitter(
                destinations=[
                    ModelEventDestination.create_file(
                        name="file", file_path=str(file_path), buffer_size=100
                    )
                ],
            )

            event = ModelContractValidationStartedEvent(
                contract_name="test",
                run_id=uuid4(),
                context=ModelContractValidationContext(),
            )
            await emitter.emit(event)

            stats = emitter.get_sink_stats()

            assert "file" in stats
            assert stats["file"]["type"] == "file"
            assert stats["file"]["event_count"] == 1
            assert "buffer_count" in stats["file"]
            assert stats["file"]["buffer_count"] == 1

    def test_sink_names_property(self) -> None:
        """Test that sink_names returns all active sink names."""
        emitter = ServiceContractValidationEventEmitter(
            destinations=[
                ModelEventDestination.create_memory(name="mem1"),
                ModelEventDestination.create_memory(name="mem2"),
            ],
        )

        names = emitter.sink_names

        assert "mem1" in names
        assert "mem2" in names
        assert len(names) == 2

    def test_default_memory_destination_created(self) -> None:
        """Test that default memory destination is created if none provided."""
        emitter = ServiceContractValidationEventEmitter()

        assert "memory" in emitter.sink_names

    def test_disabled_destination_not_created(self) -> None:
        """Test that disabled destinations are not created."""
        emitter = ServiceContractValidationEventEmitter(
            destinations=[
                ModelEventDestination(
                    destination_type=EnumEventSinkType.MEMORY,
                    destination_name="disabled",
                    enabled=False,
                ),
                ModelEventDestination.create_memory(name="enabled"),
            ],
        )

        assert "disabled" not in emitter.sink_names
        assert "enabled" in emitter.sink_names

    def test_kafka_destination_raises_not_implemented(self) -> None:
        """Test that Kafka destination raises not implemented error."""
        with pytest.raises(ModelOnexError) as exc_info:
            ServiceContractValidationEventEmitter(
                destinations=[
                    ModelEventDestination.create_kafka(
                        name="kafka",
                        topic="test.topic",
                        bootstrap_servers="localhost:9092",
                    )
                ],
            )

        assert exc_info.value.error_code == EnumCoreErrorCode.METHOD_NOT_IMPLEMENTED

    @pytest.mark.asyncio
    async def test_emit_all_event_types(self) -> None:
        """Test emitting all contract validation event types."""
        emitter = ServiceContractValidationEventEmitter(
            destinations=[ModelEventDestination.create_memory(name="memory")],
        )

        run_id = uuid4()
        events = [
            ModelContractValidationStartedEvent(
                contract_name="test",
                run_id=run_id,
                context=ModelContractValidationContext(),
            ),
            ModelContractValidationPassedEvent(
                contract_name="test",
                run_id=run_id,
                duration_ms=100,
            ),
            ModelContractValidationFailedEvent(
                contract_name="test",
                run_id=run_id,
                error_count=1,
                first_error_code="TEST_ERROR",
                duration_ms=50,
            ),
            ModelContractMergeStartedEvent(
                contract_name="test",
                run_id=run_id,
            ),
            ModelContractMergeCompletedEvent(
                contract_name="test",
                run_id=run_id,
                effective_contract_name="test-effective",
                duration_ms=75,
            ),
        ]

        for event in events:
            await emitter.emit(event)

        stored_events = emitter.get_events("memory")
        assert len(stored_events) == 5

    @pytest.mark.asyncio
    async def test_correlation_id_setter(self) -> None:
        """Test setting correlation_id after initialization."""
        emitter = ServiceContractValidationEventEmitter(
            destinations=[ModelEventDestination.create_memory(name="memory")],
        )

        assert emitter.correlation_id is None

        new_id = uuid4()
        emitter.correlation_id = new_id

        assert emitter.correlation_id == new_id

        # New events should get this correlation_id
        event = ModelContractValidationStartedEvent(
            contract_name="test",
            run_id=uuid4(),
            context=ModelContractValidationContext(),
        )
        await emitter.emit(event)

        events = emitter.get_events("memory")
        assert events[0].correlation_id == new_id


# =============================================================================
# Error Handling Tests
# =============================================================================


@pytest.mark.unit
class TestEmitterErrorHandling:
    """Tests for error handling in the emitter."""

    @pytest.mark.asyncio
    async def test_emit_with_no_sinks_raises_error(self) -> None:
        """Test that emitting with no active sinks raises error."""
        # Create emitter with disabled destination
        emitter = ServiceContractValidationEventEmitter(
            destinations=[
                ModelEventDestination(
                    destination_type=EnumEventSinkType.MEMORY,
                    destination_name="disabled",
                    enabled=False,
                )
            ],
        )

        event = ModelContractValidationStartedEvent(
            contract_name="test",
            run_id=uuid4(),
            context=ModelContractValidationContext(),
        )

        with pytest.raises(ModelOnexError) as exc_info:
            await emitter.emit(event)

        assert exc_info.value.error_code == EnumCoreErrorCode.CONFIGURATION_ERROR
        assert "No active sinks" in exc_info.value.message

    def test_file_destination_without_path_raises_error(self) -> None:
        """Test that file destination without path raises error on creation.

        Note: This validation happens at the Pydantic model level (ModelEventDestination),
        not at the ServiceContractValidationEventEmitter level.
        """
        from pydantic import ValidationError

        with pytest.raises(ValidationError) as exc_info:
            ModelEventDestination(
                destination_type=EnumEventSinkType.FILE,
                destination_name="file",
                # file_path is None
            )

        error_str = str(exc_info.value)
        assert "file_path" in error_str.lower()

    def test_clear_events_raises_for_unknown_sink(self) -> None:
        """Test that clear_events raises for unknown sink."""
        emitter = ServiceContractValidationEventEmitter(
            destinations=[ModelEventDestination.create_memory(name="known")],
        )

        with pytest.raises(ModelOnexError) as exc_info:
            emitter.clear_events("unknown")

        assert exc_info.value.error_code == EnumCoreErrorCode.NOT_FOUND

    def test_clear_events_raises_for_non_memory_sink(self) -> None:
        """Test that clear_events raises for non-memory sink."""
        with tempfile.TemporaryDirectory() as tmpdir:
            file_path = Path(tmpdir) / "test.jsonl"
            emitter = ServiceContractValidationEventEmitter(
                destinations=[
                    ModelEventDestination.create_file(
                        name="file", file_path=str(file_path)
                    )
                ],
            )

            with pytest.raises(ModelOnexError) as exc_info:
                emitter.clear_events("file")

            assert exc_info.value.error_code == EnumCoreErrorCode.INVALID_OPERATION
