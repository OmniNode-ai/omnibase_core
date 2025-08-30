# ONEX Core Coding Standards and Conventions

## Type Safety Requirements
- **ZERO tolerance for `Any` types** - all code must be strongly typed
- Use proper type hints with generics: `TypeVar("T")`, `Dict[str, Any]`, etc.
- All function signatures must include complete type annotations
- Use `Optional[T]` or `Union[T, None]` for nullable types

## Error Handling Standards
- **NEVER use generic Exception** - always use OnexError with proper error codes
- **MANDATORY exception chaining**: Use `raise OnexError(...) from e` pattern
- Use `@standard_error_handling` decorator to eliminate boilerplate
- All errors must include descriptive messages and error codes

## ONEX Architecture Patterns
- **Protocol-based DI**: Use `container.get_service("ProtocolName")` only
- **No isinstance checks**: Use duck typing through protocols
- **No registry dependencies**: Pure protocol-based resolution
- **4-Node inheritance**: Inherit from NodeEffectService, NodeComputeService, etc.

## Code Organization
- **Strong typing**: All models use Pydantic with proper field types
- **Clean imports**: Use absolute imports, avoid circular dependencies
- **Contract compliance**: All code must follow ONEX contract patterns
- **Documentation**: Use docstrings for public APIs, inline comments for complex logic

## Naming Conventions
- **Models**: Prefix with "Model" (ModelEventEnvelope, ModelHealthStatus)
- **Protocols**: Prefix with "Protocol" (ProtocolEventBus, ProtocolLogger)
- **Enums**: Prefix with "Enum" (EnumNodeType, EnumHealthStatus)
- **Services**: Descriptive names ending in "Service"
- **Variables**: snake_case for variables, UPPER_CASE for constants

## Quality Gates
- Must pass `ruff` linting with comprehensive ruleset
- Must pass `mypy` type checking with no errors
- Must follow `black` and `isort` formatting
- Must include tests for all public interfaces
- Must use proper ONEX error handling patterns
