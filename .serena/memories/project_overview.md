# ONEX Core Framework Project Overview

## Purpose
ONEX Core Framework (omnibase-core) provides foundational implementations for the ONEX framework, including base classes, dependency injection, and essential models. It implements the contracts defined in omnibase-spi and provides the foundational architecture for the 4-node ONEX pattern.

## Tech Stack
- **Python**: 3.11+
- **Package Management**: Poetry
- **Testing**: pytest with asyncio support
- **Type Checking**: mypy
- **Linting**: ruff with comprehensive rule set
- **Formatting**: black, isort
- **Dependencies**:
  - omnibase-spi (via git SSH)
  - pydantic 2.0+
  - llama-index 0.10+
  - fastapi 0.100+
  - uvicorn 0.20+

## Architecture Principles
- **Protocol-Driven Dependency Injection**: Uses ONEXContainer with `container.get_service("ProtocolName")` pattern
- **4-Node Architecture**: EFFECT → COMPUTE → REDUCER → ORCHESTRATOR workflow pattern
- **Zero Boilerplate**: Base classes eliminate 80+ lines of initialization code per tool
- **Structured Error Handling**: OnexError with Pydantic models for consistent error management
- **Event-Driven Processing**: ModelEventEnvelope for inter-service communication

## Key Components
- **Core Framework**: Node service base classes, DI container, error handling
- **Models**: Core data models and coordination models
- **Examples**: Canonical implementations of all 4 node types
- **Exceptions**: Structured error handling system
- **Decorators**: Utility decorators for common patterns
