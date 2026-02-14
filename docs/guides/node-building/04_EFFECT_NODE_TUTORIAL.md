> **Navigation**: [Home](../../INDEX.md) > [Guides](../README.md) > [Node Building](./README.md) > EFFECT Node Tutorial

> **Note**: For authoritative coding standards, see [CLAUDE.md](../../../CLAUDE.md).

# EFFECT Node Tutorial: Build a File Backup System

**Reading Time**: 30 minutes
**Difficulty**: Intermediate
**Prerequisites**: [What is a Node?](01_WHAT_IS_A_NODE.md), [Node Types](02_NODE_TYPES.md)

## Recommended Approach

This tutorial shows **TWO approaches**:

1. **RECOMMENDED (95% of use cases)**: `ModelServiceEffect` wrapper
   - Production-ready with built-in features
   - Minimal boilerplate
   - Health checks, metrics, event bus, transaction support included

2. **ADVANCED (5% of use cases)**: `NodeEffect` base class
   - Custom mixin composition
   - Selective feature inclusion
   - More control, more setup

**Start with ModelServiceEffect unless you have specific needs for NodeEffect.**

See [Node Class Hierarchy Guide](../../architecture/NODE_CLASS_HIERARCHY.md) for detailed comparison.

## What You'll Build

In this tutorial, you'll build a production-ready **File Backup Node** that:

- Performs atomic file operations with transaction support
- Implements retry logic with exponential backoff
- Uses circuit breaker patterns for resilience
- Handles rollback scenarios gracefully
- Provides comprehensive error handling

## Execution Shape

> **Canonical Execution Shape**: EFFECT nodes execute **Intent to Effect** operations.
> They receive Intents from REDUCER nodes or Actions from ORCHESTRATOR nodes and perform the actual I/O.
> See [Canonical Execution Shapes](../../architecture/CANONICAL_EXECUTION_SHAPES.md) for the complete pattern.

---

## Handler Architecture

> **Architectural Rule**: Nodes are thin coordination shells. Business logic belongs in **handlers**, not in the node class itself. The node delegates to a handler, and the handler returns a `ModelHandlerOutput`.

### EFFECT Output Constraints

| Field | COMPUTE | EFFECT | REDUCER | ORCHESTRATOR |
|-------|---------|--------|---------|--------------|
| `result` | Required | **Forbidden** | Forbidden | Forbidden |
| `events[]` | Forbidden | **Allowed** | Forbidden | Allowed |
| `intents[]` | Forbidden | Forbidden | Forbidden | Allowed |
| `projections[]` | Forbidden | Forbidden | Allowed | Forbidden |

EFFECT nodes return **events** describing what happened (e.g., "file backed up", "API called"). They do NOT return a typed `result` -- that is exclusive to COMPUTE nodes.

### Handler-Based Pattern (Recommended)

In production ONEX code, the EFFECT node delegates I/O execution to a handler. The handler returns `ModelHandlerOutput.for_effect(events=[...])`:

```python
from omnibase_core.models.dispatch.model_handler_output import ModelHandlerOutput
from omnibase_core.models.events.model_event_envelope import ModelEventEnvelope


class HandlerFileBackup:
    """Handler containing the actual I/O logic for file backups."""

    async def execute(
        self,
        envelope: ModelOnexEnvelope,
        input_data: ModelFileBackupInput,
    ) -> ModelHandlerOutput:
        """
        Execute file backup and return events describing what happened.

        Args:
            envelope: The incoming ONEX envelope (provides IDs for tracing)
            input_data: File backup input configuration

        Returns:
            ModelHandlerOutput with events (EFFECT constraint).
        """
        # Perform actual I/O
        source_content = input_data.source_path.read_bytes()
        input_data.backup_path.parent.mkdir(parents=True, exist_ok=True)
        input_data.backup_path.write_bytes(source_content)

        # EFFECT nodes return events, NOT result
        backup_event = ModelEventEnvelope(
            event_type="file.backed_up",
            payload={
                "source_path": str(input_data.source_path),
                "backup_path": str(input_data.backup_path),
                "size_bytes": len(source_content),
            },
        )

        return ModelHandlerOutput.for_effect(
            input_envelope_id=envelope.metadata.envelope_id,
            correlation_id=envelope.metadata.correlation_id,
            events=[backup_event],
        )


class NodeFileBackupEffect(NodeEffect):
    """Thin shell -- delegates to handler."""

    def __init__(self, container: ModelONEXContainer) -> None:
        super().__init__(container)
        # Production code should resolve the handler via container DI:
        #   self._handler = container.get_service(ProtocolFileBackupHandler)
        self._handler = HandlerFileBackup()

    async def process(self, input_data):
        return await self._handler.execute(input_data)
```

The tutorial below shows I/O logic inline for teaching clarity. In production, always extract logic into a handler.

---

**Why EFFECT Nodes?**

EFFECT nodes handle all external interactions in the ONEX architecture:
- File I/O operations
- Database operations
- API calls
- Event emission
- Any operation with side effects

**Tutorial Structure**:
1. Define input/output models
2. Create the EFFECT node implementation
3. Write comprehensive tests
4. See it in action with usage examples

---

## Prerequisites Check

Before starting, verify your environment:

```bash
# Check Poetry is installed
poetry --version

# Verify you're in the omnibase_core directory
pwd  # Should end with /omnibase_core

# Install dependencies
poetry install

# Run a quick test to ensure everything works
poetry run pytest tests/unit/nodes/test_node_effect.py -v -k "test_file_operation" --maxfail=1
```

If tests pass, you're ready to begin!
If tests fail, see [Troubleshooting](#troubleshooting) at the end of this guide.

---

## Step 1: Define Input Model

**File**: `src/your_project/nodes/model_file_backup_input.py`

EFFECT nodes use **ModelEffectInput** as a base, but we'll create a domain-specific model for clarity:

```python
"""Input model for file backup EFFECT node."""

from pathlib import Path
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field


class ModelFileBackupInput(BaseModel):
    """
    Input configuration for file backup operations.

    This model defines what data the EFFECT node receives
    to perform file backup operations with transaction support.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    # Source file to back up
    source_path: Path = Field(
        ...,
        description="Path to the source file to back up",
    )

    # Backup destination
    backup_path: Path = Field(
        ...,
        description="Path where backup should be created",
    )

    # Operation configuration
    atomic: bool = Field(
        default=True,
        description="Whether to use atomic operations (recommended)",
    )

    verify_backup: bool = Field(
        default=True,
        description="Whether to verify backup after creation",
    )

    # Retry configuration
    max_retries: int = Field(
        default=3,
        ge=0,
        le=10,
        description="Maximum number of retry attempts on failure",
    )

    retry_delay_ms: int = Field(
        default=1000,
        ge=100,
        le=30000,
        description="Initial retry delay in milliseconds (exponential backoff)",
    )

    # Operation tracking
    operation_id: UUID = Field(
        default_factory=uuid4,
        description="Unique identifier for this operation",
    )

    # Metadata for logging and tracing
    metadata: dict[str, str] = Field(
        default_factory=dict,
        description="Additional metadata for operation tracing",
    )
```

**Key Points**:
- Uses Pydantic v2 `ConfigDict` for configuration
- Immutable (`frozen=True`) for safety
- Descriptive field documentation
- Sensible defaults with validation constraints
- UUID tracking for operations

---

## Step 2: Define Output Model

**File**: `src/your_project/nodes/model_file_backup_output.py`

```python
"""Output model for file backup EFFECT node."""

from datetime import datetime
from pathlib import Path
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class ModelFileBackupOutput(BaseModel):
    """
    Output results from file backup operations.

    This model defines what data the EFFECT node returns
    after completing backup operations.
    """

    model_config = ConfigDict(frozen=True)

    # Operation result
    success: bool = Field(
        ...,
        description="Whether the backup operation succeeded",
    )

    # File information
    source_path: Path = Field(
        ...,
        description="Original source file path",
    )

    backup_path: Path = Field(
        ...,
        description="Created backup file path",
    )

    source_size_bytes: int = Field(
        ...,
        ge=0,
        description="Size of source file in bytes",
    )

    backup_size_bytes: int = Field(
        ...,
        ge=0,
        description="Size of backup file in bytes",
    )

    # Verification result
    verified: bool = Field(
        default=False,
        description="Whether backup was verified",
    )

    checksum_match: bool | None = Field(
        default=None,
        description="Whether checksums match (if verification enabled)",
    )

    # Transaction details
    transaction_id: UUID | None = Field(
        default=None,
        description="Transaction ID if atomic operation was used",
    )

    rollback_performed: bool = Field(
        default=False,
        description="Whether rollback was performed due to error",
    )

    # Performance metrics
    processing_time_ms: float = Field(
        ...,
        ge=0,
        description="Total processing time in milliseconds",
    )

    retry_count: int = Field(
        default=0,
        ge=0,
        description="Number of retries performed",
    )

    # Operation tracking
    operation_id: UUID = Field(
        ...,
        description="Unique identifier for this operation",
    )

    completed_at: datetime = Field(
        default_factory=datetime.now,
        description="Timestamp when operation completed",
    )

    # Error information (if applicable)
    error_message: str | None = Field(
        default=None,
        description="Error message if operation failed",
    )
```

**Key Points**:
- Uses Pydantic v2 `ConfigDict` for configuration
- Comprehensive result information
- Transaction tracking for rollback scenarios
- Performance metrics included
- Error details when failures occur
- Verification results for data integrity

---

## Step 3: Implement the EFFECT Node

### RECOMMENDED: Using ModelServiceEffect Wrapper

For **95% of use cases**, use the production-ready `ModelServiceEffect` wrapper that includes all standard features:

**File**: `src/your_project/nodes/node_file_backup_effect.py`

> **Tutorial Simplification**: The example below places logic directly in the node class for clarity. In production, always use the [handler delegation pattern](#handler-architecture) shown above -- nodes must be thin shells that delegate to handlers.

```python
"""
File Backup EFFECT Node - Production Implementation.

Demonstrates EFFECT node capabilities:
- Atomic file operations with transactions
- Retry logic with exponential backoff
- Circuit breaker patterns
- Rollback on failures
- Comprehensive error handling
"""

import hashlib
import time
from pathlib import Path

from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.enums.enum_effect_types import EnumEffectType
from omnibase_core.enums.enum_log_level import EnumLogLevel as LogLevel
from omnibase_core.errors import ModelOnexError
from omnibase_core.infrastructure.infra_bases import ModelServiceEffect
from omnibase_core.logging.logging_structured import emit_log_event_sync as emit_log_event
from omnibase_core.models.container.model_onex_container import ModelONEXContainer
from omnibase_core.nodes import ModelEffectInput, ModelEffectOutput

from your_project.nodes.model_file_backup_input import ModelFileBackupInput
from your_project.nodes.model_file_backup_output import ModelFileBackupOutput


class NodeFileBackupEffect(ModelServiceEffect):
    """
    File Backup EFFECT Node.

    Performs atomic file backup operations with transaction support,
    retry logic, and verification capabilities.

    Key Features:
    - Atomic file operations (using temp files + rename)
    - Transaction support with automatic rollback
    - Retry logic with exponential backoff
    - Checksum verification of backups
    - Circuit breaker for repeated failures
    - Comprehensive error handling and logging
    """

    def __init__(self, container: ModelONEXContainer) -> None:
        """Initialize file backup EFFECT node."""
        super().__init__(container)

        # Track backup statistics
        self.backup_stats = {
            "total_backups": 0,
            "successful_backups": 0,
            "failed_backups": 0,
            "total_bytes_backed_up": 0,
        }

    async def backup_file(
        self,
        input_data: ModelFileBackupInput,
    ) -> ModelFileBackupOutput:
        """
        Perform file backup operation with full EFFECT capabilities.

        Args:
            input_data: Backup configuration and parameters

        Returns:
            ModelFileBackupOutput: Backup results with verification

        Raises:
            ModelOnexError: If backup fails after all retries
        """
        start_time = time.time()

        # Convert domain model to ModelEffectInput
        effect_input = self._convert_to_effect_input(input_data)

        # Execute via base NodeEffect.process() for retry/circuit breaker support
        try:
            effect_output = await self.process(effect_input)

            # Extract results from effect output
            result_data = effect_output.result

            # Build output model
            output = ModelFileBackupOutput(
                success=True,
                source_path=input_data.source_path,
                backup_path=input_data.backup_path,
                source_size_bytes=result_data.get("source_size_bytes", 0),
                backup_size_bytes=result_data.get("backup_size_bytes", 0),
                verified=result_data.get("verified", False),
                checksum_match=result_data.get("checksum_match"),
                transaction_id=effect_output.operation_id,
                rollback_performed=False,
                processing_time_ms=effect_output.processing_time_ms,
                retry_count=effect_output.retry_count,
                operation_id=input_data.operation_id,
            )

            # Update statistics
            self.backup_stats["total_backups"] += 1
            self.backup_stats["successful_backups"] += 1
            self.backup_stats["total_bytes_backed_up"] += output.backup_size_bytes

            emit_log_event(
                LogLevel.INFO,
                f"File backup successful: {input_data.source_path} -> {input_data.backup_path}",
                {
                    "node_id": str(self.node_id),
                    "operation_id": str(input_data.operation_id),
                    "source_size_bytes": output.source_size_bytes,
                    "processing_time_ms": output.processing_time_ms,
                    "retry_count": output.retry_count,
                },
            )

            return output

        except ModelOnexError as e:
            processing_time = (time.time() - start_time) * 1000

            # Update failure statistics
            self.backup_stats["total_backups"] += 1
            self.backup_stats["failed_backups"] += 1

            emit_log_event(
                LogLevel.ERROR,
                f"File backup failed: {e.message}",
                {
                    "node_id": str(self.node_id),
                    "operation_id": str(input_data.operation_id),
                    "source_path": str(input_data.source_path),
                    "error": str(e),
                },
            )

            # Return failure output
            return ModelFileBackupOutput(
                success=False,
                source_path=input_data.source_path,
                backup_path=input_data.backup_path,
                source_size_bytes=0,
                backup_size_bytes=0,
                rollback_performed=True,
                processing_time_ms=processing_time,
                operation_id=input_data.operation_id,
                error_message=e.message,
            )

    def _convert_to_effect_input(
        self,
        input_data: ModelFileBackupInput,
    ) -> ModelEffectInput:
        """Convert domain model to base ModelEffectInput."""
        return ModelEffectInput(
            effect_type=EnumEffectType.FILE_OPERATION,
            operation_data={
                "operation_type": "backup",
                "source_path": str(input_data.source_path),
                "backup_path": str(input_data.backup_path),
                "atomic": input_data.atomic,
                "verify_backup": input_data.verify_backup,
            },
            operation_id=input_data.operation_id,
            transaction_enabled=input_data.atomic,
            retry_enabled=True,
            max_retries=input_data.max_retries,
            retry_delay_ms=input_data.retry_delay_ms,
            circuit_breaker_enabled=True,
            metadata=input_data.metadata,
        )

    async def _execute_effect(
        self,
        input_data: ModelEffectInput,
        transaction: object | None,
    ) -> dict[str, object]:
        """
        Execute the actual backup operation.

        This method is called by NodeEffect.process() and handles
        the core backup logic.
        """
        operation_data = input_data.operation_data
        source_path = Path(operation_data["source_path"])
        backup_path = Path(operation_data["backup_path"])
        atomic = operation_data.get("atomic", True)
        verify = operation_data.get("verify_backup", True)

        # Validate source file exists
        if not source_path.exists():
            raise ModelOnexError(
                error_code=EnumCoreErrorCode.RESOURCE_UNAVAILABLE,
                message=f"Source file not found: {source_path}",
                context={
                    "node_id": str(self.node_id),
                    "source_path": str(source_path),
                },
            )

        # Create backup directory if needed
        backup_path.parent.mkdir(parents=True, exist_ok=True)

        # Perform atomic backup
        if atomic:
            result = await self._atomic_backup(
                source_path,
                backup_path,
                verify,
                transaction,
            )
        else:
            result = await self._simple_backup(
                source_path,
                backup_path,
                verify,
            )

        return result

    async def _atomic_backup(
        self,
        source_path: Path,
        backup_path: Path,
        verify: bool,
        transaction: object | None,
    ) -> dict[str, object]:
        """Perform atomic backup using temp file + rename pattern."""
        temp_backup = backup_path.with_suffix(backup_path.suffix + ".tmp")

        try:
            # Read source file
            source_content = source_path.read_bytes()
            source_size = len(source_content)

            # Calculate source checksum if verification enabled
            source_checksum = None
            if verify:
                source_checksum = hashlib.sha256(source_content).hexdigest()

            # Write to temp file
            temp_backup.write_bytes(source_content)

            # Atomically rename temp to final
            temp_backup.replace(backup_path)

            # Register rollback operation if transaction active
            if transaction and hasattr(transaction, "add_operation"):

                def rollback_backup() -> None:
                    """Rollback function to delete backup on failure."""
                    if backup_path.exists():
                        backup_path.unlink()

                transaction.add_operation(
                    "file_backup",
                    {"backup_path": str(backup_path)},
                    rollback_backup,
                )

            # Verify backup if requested
            verified = False
            checksum_match = None

            if verify:
                backup_content = backup_path.read_bytes()
                backup_checksum = hashlib.sha256(backup_content).hexdigest()
                checksum_match = source_checksum == backup_checksum
                verified = True

                if not checksum_match:
                    raise ModelOnexError(
                        error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                        message="Backup verification failed - checksum mismatch",
                        context={
                            "source_checksum": source_checksum,
                            "backup_checksum": backup_checksum,
                        },
                    )

            return {
                "source_size_bytes": source_size,
                "backup_size_bytes": len(source_content),
                "verified": verified,
                "checksum_match": checksum_match,
                "backup_path": str(backup_path),
            }

        except Exception:
            # Clean up temp file on error
            if temp_backup.exists():
                temp_backup.unlink()
            raise

    async def _simple_backup(
        self,
        source_path: Path,
        backup_path: Path,
        verify: bool,
    ) -> dict[str, object]:
        """Perform simple (non-atomic) backup."""
        source_content = source_path.read_bytes()
        backup_path.write_bytes(source_content)

        verified = False
        checksum_match = None

        if verify:
            backup_content = backup_path.read_bytes()
            source_checksum = hashlib.sha256(source_content).hexdigest()
            backup_checksum = hashlib.sha256(backup_content).hexdigest()
            checksum_match = source_checksum == backup_checksum
            verified = True

        return {
            "source_size_bytes": len(source_content),
            "backup_size_bytes": len(source_content),
            "verified": verified,
            "checksum_match": checksum_match,
            "backup_path": str(backup_path),
        }

    def get_backup_stats(self) -> dict[str, float]:
        """Get backup statistics for monitoring."""
        return {
            **self.backup_stats,
            "success_rate": (
                self.backup_stats["successful_backups"]
                / max(self.backup_stats["total_backups"], 1)
            )
            * 100,
        }
```

**What `ModelServiceEffect` Provides**:
- **Health Checks**: Built-in readiness and liveness endpoints
- **Metrics**: Automatic prometheus-style metrics tracking
- **Event Bus**: Kafka/Redpanda integration for event publishing
- **Circuit Breaker**: Automatic failure protection
- **Transaction Management**: Built-in `ModelEffectTransaction` with rollback support
- **Retry Logic**: Exponential backoff retry mechanism
- **Circuit Breakers**: Per-service circuit breaker patterns
- **Effect Handlers**: Registry for custom effect operations
- **Concurrency Control**: Semaphore for limiting concurrent effects
- **Performance Tracking**: Built-in metrics for effect execution
- **Configuration Support**: Automatic config loading from `NodeConfigProvider`

**Key Implementation Features**:

- **Atomic Operations**: Uses temp file + rename pattern for safety
- **Transaction Support**: Automatic rollback on failures
- **Retry Logic**: Inherited from base classes
- **Circuit Breaker**: Prevents cascading failures
- **Checksum Verification**: Ensures backup integrity
- **Comprehensive Logging**: Full operation traceability
- **Statistics Tracking**: Monitor performance and reliability

### When to Use Which Approach

| Feature | ModelServiceEffect | NodeEffect |
|---------|-------------------|------------|
| **Health Checks** | Included | Manual setup |
| **Metrics** | Included | Manual setup |
| **Event Bus** | Included | Manual setup |
| **Circuit Breaker** | Included | Included |
| **Transaction Support** | Included | Included |
| **Setup Complexity** | Minimal | Moderate |
| **Production Ready** | Yes | Requires configuration |
| **Use Case** | 95% of applications | Custom mixin composition |

### ADVANCED: Using NodeEffect Base Class

For **5% of use cases** where you need custom mixin composition:

```python
from omnibase_core.models.container.model_onex_container import ModelONEXContainer
from omnibase_core.nodes import NodeEffect


class NodeFileBackupEffect(NodeEffect):
    """
    EFFECT node with custom mixin composition.

    Use this approach when:
    - You need specific mixin combinations not in ModelServiceEffect
    - You want fine-grained control over transaction logic
    - You're implementing non-standard effect patterns
    """

    def __init__(self, container: ModelONEXContainer) -> None:
        super().__init__(container)

        # Manually initialize effect-specific features
        self.active_transactions: dict = {}
        self.circuit_breakers: dict = {}
        self.effect_handlers: dict = {}
        # ... rest of manual setup

    # ... rest of implementation (same as above)
```

**When to use NodeEffect**:
- Custom transaction management beyond ModelEffectTransaction
- Custom mixin combinations beyond ModelServiceEffect
- Non-standard retry/circuit breaker strategies
- Special effect handler registration needs

**When to use ModelServiceEffect** (recommended):
- Standard EFFECT operations (95% of cases)
- File I/O, database, API calls
- Production deployment
- Need health checks, metrics, event bus out-of-the-box
- Following ONEX best practices

---

## Step 4: Write Comprehensive Tests

**File**: `tests/unit/nodes/test_node_file_backup_effect.py`

```python
"""Tests for NodeFileBackupEffect."""

import tempfile
from pathlib import Path

import pytest

from omnibase_core.models.container.model_onex_container import ModelONEXContainer

from your_project.nodes.model_file_backup_input import ModelFileBackupInput
from your_project.nodes.node_file_backup_effect import NodeFileBackupEffect


@pytest.fixture
def container():
    """Create test container."""
    return ModelONEXContainer()


@pytest.fixture
def backup_node(container):
    """Create file backup node instance."""
    return NodeFileBackupEffect(container)


@pytest.fixture
def temp_source_file():
    """Create temporary source file for testing."""
    with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".txt") as f:
        f.write("Test file content for backup\n" * 100)
        source_path = Path(f.name)

    yield source_path

    # Cleanup
    if source_path.exists():
        source_path.unlink()


@pytest.mark.asyncio
async def test_successful_backup(backup_node, temp_source_file, tmp_path):
    """Test successful file backup operation."""
    backup_path = tmp_path / "backup.txt"

    input_data = ModelFileBackupInput(
        source_path=temp_source_file,
        backup_path=backup_path,
        atomic=True,
        verify_backup=True,
    )

    result = await backup_node.backup_file(input_data)

    # Verify result
    assert result.success is True
    assert result.backup_path == backup_path
    assert result.verified is True
    assert result.checksum_match is True
    assert backup_path.exists()
    assert result.source_size_bytes > 0
    assert result.backup_size_bytes == result.source_size_bytes


@pytest.mark.asyncio
async def test_backup_with_verification(backup_node, temp_source_file, tmp_path):
    """Test backup with checksum verification."""
    backup_path = tmp_path / "verified_backup.txt"

    input_data = ModelFileBackupInput(
        source_path=temp_source_file,
        backup_path=backup_path,
        verify_backup=True,
    )

    result = await backup_node.backup_file(input_data)

    assert result.verified is True
    assert result.checksum_match is True

    # Verify content matches exactly
    assert temp_source_file.read_bytes() == backup_path.read_bytes()


@pytest.mark.asyncio
async def test_backup_nonexistent_source(backup_node, tmp_path):
    """Test backup fails gracefully for nonexistent source."""
    source_path = Path("/nonexistent/file.txt")
    backup_path = tmp_path / "backup.txt"

    input_data = ModelFileBackupInput(
        source_path=source_path,
        backup_path=backup_path,
    )

    result = await backup_node.backup_file(input_data)

    assert result.success is False
    assert result.error_message is not None
    assert not backup_path.exists()


@pytest.mark.asyncio
async def test_backup_creates_directory(backup_node, temp_source_file, tmp_path):
    """Test backup creates parent directories if needed."""
    backup_path = tmp_path / "nested" / "dir" / "backup.txt"

    input_data = ModelFileBackupInput(
        source_path=temp_source_file,
        backup_path=backup_path,
    )

    result = await backup_node.backup_file(input_data)

    assert result.success is True
    assert backup_path.exists()
    assert backup_path.parent.exists()


@pytest.mark.asyncio
async def test_backup_statistics_tracking(backup_node, temp_source_file, tmp_path):
    """Test that backup statistics are tracked correctly."""
    backup_path = tmp_path / "backup.txt"

    initial_stats = backup_node.get_backup_stats()

    input_data = ModelFileBackupInput(
        source_path=temp_source_file,
        backup_path=backup_path,
    )

    await backup_node.backup_file(input_data)

    final_stats = backup_node.get_backup_stats()

    assert final_stats["total_backups"] == initial_stats["total_backups"] + 1
    assert final_stats["successful_backups"] == initial_stats["successful_backups"] + 1
    assert final_stats["total_bytes_backed_up"] > initial_stats["total_bytes_backed_up"]
```

**Testing Best Practices**:

- **Fixtures** for reusable test setup
- **Async tests** using `pytest.mark.asyncio`
- **Edge cases** covered (missing files, directory creation)
- **Statistics validation** confirms tracking works
- **Cleanup** ensures no test pollution

---

## Step 5: Usage Examples

### Basic File Backup

```python
import asyncio
from pathlib import Path

from omnibase_core.models.container.model_onex_container import ModelONEXContainer

from your_project.nodes.model_file_backup_input import ModelFileBackupInput
from your_project.nodes.node_file_backup_effect import NodeFileBackupEffect


async def backup_important_file():
    """Backup an important configuration file."""
    container = ModelONEXContainer()
    backup_node = NodeFileBackupEffect(container)

    input_data = ModelFileBackupInput(
        source_path=Path("/etc/important_config.yaml"),
        backup_path=Path("/backups/important_config.backup.yaml"),
        atomic=True,
        verify_backup=True,
        max_retries=3,
    )

    result = await backup_node.backup_file(input_data)

    if result.success:
        print("Backup successful!")
        print(f"   Size: {result.backup_size_bytes} bytes")
        print(f"   Verified: {result.checksum_match}")
        print(f"   Time: {result.processing_time_ms:.2f}ms")
    else:
        print(f"Backup failed: {result.error_message}")


asyncio.run(backup_important_file())
```

### Batch Backup with Error Handling

```python
from pathlib import Path

from omnibase_core.models.container.model_onex_container import ModelONEXContainer

from your_project.nodes.model_file_backup_input import ModelFileBackupInput
from your_project.nodes.node_file_backup_effect import NodeFileBackupEffect


async def backup_multiple_files(file_list: list[Path], backup_dir: Path):
    """Backup multiple files with comprehensive error handling."""
    container = ModelONEXContainer()
    backup_node = NodeFileBackupEffect(container)

    results = []

    for source_file in file_list:
        backup_path = backup_dir / f"{source_file.name}.backup"

        input_data = ModelFileBackupInput(
            source_path=source_file,
            backup_path=backup_path,
            max_retries=2,
        )

        result = await backup_node.backup_file(input_data)
        results.append((source_file, result))

    # Report results
    successful = sum(1 for _, r in results if r.success)
    failed = len(results) - successful

    print("\nBackup Summary:")
    print(f"   Total: {len(results)}")
    print(f"   Successful: {successful}")
    print(f"   Failed: {failed}")

    # Get statistics
    stats = backup_node.get_backup_stats()
    print("\nNode Statistics:")
    print(f"   Success Rate: {stats['success_rate']:.1f}%")
    print(f"   Total Bytes: {stats['total_bytes_backed_up']:,}")
```

---

## Troubleshooting

### Tests Failing

**Problem**: Tests fail with "container not configured"

**Solution**:
```python
# Ensure container has required services
container = ModelONEXContainer()
# Add any required service registrations
```

**Problem**: Permission errors during backup

**Solution**:
```python
# Use temp directories for tests
import tempfile
with tempfile.TemporaryDirectory() as tmpdir:
    backup_path = Path(tmpdir) / "backup.txt"
```

---

## Quick Reference

### EFFECT Node Capabilities

| Feature | Purpose | Example |
|---------|---------|---------|
| **Atomic Operations** | Safe file writes | Temp file + rename |
| **Transactions** | Rollback on failure | Transaction context manager |
| **Retry Logic** | Handle transient errors | Max retries + backoff |
| **Circuit Breaker** | Prevent cascading failures | Auto-open after N failures |
| **Verification** | Ensure data integrity | Checksum validation |

### Key Methods

```python
# Core EFFECT methods
await node.process(effect_input)  # Execute with retry/circuit breaker
await node.execute_file_operation(...)  # File I/O helper
await node.emit_state_change_event(...)  # Event emission
await node.transaction_context(operation_id)  # Transaction mgmt
```

### v0.4.0 Import Pattern

```python
# All node classes and I/O models from omnibase_core.nodes
from omnibase_core.nodes import (
    NodeEffect,
    ModelEffectInput,
    ModelEffectOutput,
    ModelEffectTransaction,
)

# Container for dependency injection
from omnibase_core.models.container.model_onex_container import ModelONEXContainer

# Service wrapper for production use
from omnibase_core.infrastructure.infra_bases import ModelServiceEffect

# Error handling
from omnibase_core.errors import ModelOnexError
from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode

# Effect types
from omnibase_core.enums.enum_effect_types import (
    EnumEffectType,
    EnumTransactionState,
)
```

---

## Next Steps

Congratulations! You've built a production-ready EFFECT node!

**Continue your journey**:
- [REDUCER Node Tutorial](05_REDUCER_NODE_TUTORIAL.md) - Learn data aggregation
- [ORCHESTRATOR Node Tutorial](06_ORCHESTRATOR_NODE_TUTORIAL.md) - Master workflow coordination
- [Patterns Catalog](07_PATTERNS_CATALOG.md) - Common EFFECT patterns
- [Testing Intent Publisher](09_TESTING_INTENT_PUBLISHER.md) - Advanced testing strategies

**Challenge**: Extend this node to support S3 backups using external service integration!

---

**Last Updated**: 2025-12-13
**Framework Version**: omnibase_core 0.4.0+
**Tutorial Status**: Complete
