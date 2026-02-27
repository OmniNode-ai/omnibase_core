# Changelog

All notable changes to the ONEX Core Framework (omnibase_core) will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.21.0] - 2026-02-27

### Changed
- Version bump as part of coordinated OmniNode platform release run release-20260227-eceed7

## [0.20.0] - 2026-02-25

### Added

- **Overlay stacking pipeline** [OMN-2757] (#563): Implement overlay stacking pipeline and wire `overlay_refs` for composable contract overlays
- **Configurable validation strictness levels** [OMN-840] (#550): Add configurable strictness levels to the validation framework, enabling graduated enforcement from advisory to hard-fail
- **Contract graph navigation module** [OMN-2540/2546/2554/2561] (#536): Implement graph-based contract navigation for traversing dependency relationships across the ONEX contract graph
- **ModelRagQueries + `to_routing_config()` converter** [OMN-407] (#543): Add `ModelRagQueries`, `rag_queries` field to contracts, and `to_routing_config()` converter for RAG-driven routing
- **ValidatorNode base class and validator registry** [OMN-2550] (#552): Implement `ValidatorNode` base class and `ValidatorRegistry` for declarative validator discovery and dispatch
- **ValidationRequest, ValidationFinding, ValidationReport, ValidatorDescriptor** [OMN-2543] (#542): Add core validation data models for structured validation workflows — findings, reports, and validator descriptors
- **Core data models for objective functions and reward architecture** [OMN-2537] (#538): Implement Pydantic models for objective functions, reward signals, and reward architecture contracts
- **`check_name` validator for required-checks drift prevention** (#533): Add `ValidatorCheckName` to detect drift between declared required status checks and actual workflow job names
- **Core event models for GitHub PR, Git hook, and Linear snapshot** [OMN-2655] (#531): Add `ModelGitHubPREvent`, `ModelGitHookEvent`, and `ModelLinearSnapshot` for cross-tool event sourcing
- **`ValidatorLocalPaths` for hardcoded machine path detection** (#530): Add validator that detects hardcoded absolute machine paths in source files to prevent environment-specific drift
- **Publish-on-tag CI release workflow**: Add `release.yml` triggered by `v*.*.*` tags that validates version alignment, builds wheel + sdist, publishes to PyPI via `PYPI_TOKEN`, generates checksums, and creates a GitHub Release with artifacts

### Fixed

- **Class identity regression in fingerprint scanner** [OMN-2537] (#557): Resolve class identity regression where fingerprint scanner incorrectly resolved class references across module boundaries

## [0.19.0] - 2026-02-23

### Added

- **Intent Intelligence Pydantic models** [OMN-2486] (#526): Defined core models for the Intent Intelligence Framework — typed intent classifications, confidence scoring, and session-scoped intent graphs
- **DecisionRecord Pydantic model and schema** [OMN-2464] (#528): Implemented `DecisionRecord` contract model for tracking agent model-selection decisions with full scoring breakdown and rationale
- **ModelProjectionIntent + core projection types** [OMN-2460] (#523): Defined `ModelProjectionIntent` and supporting projection type contracts for the Projector-as-Effect-Node refactor
- **EnumAgentState + ModelAgentStatusEvent** [OMN-1847] (#520): Implemented agent state enum and status event model for lifecycle observability
- **Timeout configuration in ModelPerformanceRequirements** [OMN-1548] (#524): Added timeout fields to the performance requirements contract schema

### Changed

- **NodeReducer emits ModelProjectionIntent as blocking effect** [OMN-2509] (#527): NodeReducer now emits `ModelProjectionIntent` as a synchronous blocking effect before Kafka publish, enabling projection-as-effect-node pattern
- **Standardized Makefile with CI-parity targets** [OMN-2335] (#525): Added top-level `Makefile` with `lint`, `type-check`, `test`, `test-unit`, `test-integration`, and `ci` targets matching CI pipeline behaviour

### Dependencies

- **redis** (#517): Updated redis dev dependency to latest version

## [0.18.1] - 2026-02-19

### Added

- **SPDX MIT license headers** (#518): Added SPDX-FileCopyrightText and SPDX-License-Identifier headers to all source files for OSS compliance

### Changed

- **Repository references in CLAUDE_CODE_HOOKS.md** (#508): Updated repository references to reflect current repo structure

### Fixed

- **Mermaid diagram compatibility** (#514): Improved mermaid diagram syntax for broader rendering compatibility across documentation viewers

### Dependencies

- **sqlglot** (#516): Updated sqlglot dev dependency to latest version
- **ruff** (#515): Updated ruff linter to latest version

## [0.18.0] - 2026-02-15

### Added

- **Migrate from Poetry to uv** [OMN-2232] (#512): Full build system migration from Poetry to uv for faster dependency resolution and simpler tooling
  - Replaced `poetry.lock` with `uv.lock`
  - Updated all CI workflows and developer commands to use `uv run`
  - Consolidated `pyproject.toml` configuration for uv compatibility

- **Quality Gate, detect-secrets, and CI Summary** [OMN-2226] (#510): Enhanced CI pipeline with automated quality enforcement
  - Added quality gate workflow for merge-blocking checks
  - Integrated detect-secrets for credential leak prevention
  - CI summary report for at-a-glance pipeline status

- **Required Status Checks for Branch Protection** [OMN-2183] (#504): Added required status checks to branch protection rules for stricter merge enforcement

### Changed

- **CI/CD Standards Document** [OMN-2224] (#511): Added comprehensive CI/CD standards documentation for cross-repo consistency

- **Comprehensive Documentation Audit** (#509): Reviewed 141 documentation files for accuracy and consistency
  - Consolidated and removed stale documentation
  - Refactored CLAUDE.md to reference shared standards (#505, #506)

- **Handshake Documentation Update** (#507): Updated omnidash route count and path alias in architecture handshake

## [0.17.0] - 2026-02-12

### Added

- **GeometricConflictClassifier for Parallel Agent Output Analysis** [OMN-1854] (#502): Deterministic classifier that analyzes parallel agent outputs and classifies conflicts geometrically using similarity metrics
  - `classify()` is DETERMINISTIC (D4): same inputs always produce same output
  - `recommend_resolution()` is ADVISORY ONLY (GI-3): raises ValueError for OPPOSITE/AMBIGUOUS conflicts requiring human approval
  - Similarity engine handles dicts, strings, lists, and primitives
  - Contradiction detection for boolean and semantic opposites
  - Orthogonality detection for non-overlapping dict changes
  - 49 unit tests covering all classification thresholds

- **DB Ownership CI Twin for Runtime Assertion B1** [OMN-2150] (#501): CI workflow that provisions a temporary SQLite database, runs migrations, and verifies owner_service matches expectations
  - `ModelDbOwnershipMetadata`: Pydantic model for db_metadata table schema with naive datetime rejection
  - `validate_db_ownership`: contract-level ownership validator with `@validation_error_handling`
  - `scripts/check_db_ownership.py`: CI twin script (5 checks) with single-row constraint (`CHECK(id=1)`)
  - `check-db-ownership.yml`: GitHub Actions workflow
  - 16 unit tests covering model, validator, and CI twin logic

- **Geometric Conflict Detail Models** [OMN-1853] (#500): Rich conflict analysis models for parallel agent output classification
  - `ModelGeometricConflictDetails`: similarity metrics, multi-axis analysis, and advisory recommendations
  - `ModelConflictResolutionResult`: resolution tracking with GI-3 enforcement (OPPOSITE/AMBIGUOUS require human approval)
  - `AUTO_RESOLVABLE_TYPES` frozenset for consistent conflict resolution routing
  - `validate_assignment=True` for merge package consistency

- **Geometric Conflict Types in EnumMergeConflictType** [OMN-1852] (#499): 6 geometric conflict types from the Neumann pattern for classifying parallel agent output relationships
  - ORTHOGONAL, LOW_CONFLICT, IDENTICAL, OPPOSITE, CONFLICTING, AMBIGUOUS
  - GI-3 invariant: OPPOSITE and AMBIGUOUS require human approval

- **Handshake Policy Gate for Cross-Repo Compliance** [OMN-2086] (#498): Scheduled workflow and script that queries GitHub API to verify all active repos have check-handshake CI enforcement passing
  - Shared `repos.conf` for DRY repo list management
  - `_parse_repos_conf.sh` helper for portable parsing (bash 3.2+)
  - `POLICY_GATE_TOKEN` for cross-repo private workflow access
  - Server-side branch filtering, URL-encoded branch names, `jq` dependency documented

- **Handshake Self-Check Enforcement** [OMN-2083] (#497): CI workflow so omnibase_core verifies its own installed handshake matches the canonical source
  - `.gitignore` updated for `.claude/*` with negation for `architecture-handshake.md`
  - 9 universal platform-wide rules added to all 8 architecture handshakes
  - Frozen 4 boundary-crossing models (`ModelOnexEnvelope`, `ModelOnexEnvelopeV1`, `ModelEnvelopeMetadata`, `ModelExtensionData`) with `frozen=True` + `from_attributes=True`

### Fixed

- **Break Circular Import in FSM Package** [OMN-2048] (#496): Resolved circular import chain (`fsm/__init__` → `model_fsm_transition_result` → `reducer/__init__` → ... → `model_fsm_transition_result`)
  - Deferred `ModelFSMTransitionResult` import to `TYPE_CHECKING` + function-local import in `util_fsm_executor.py`
  - Replaced eager re-exports in `models/invariant/__init__.py` with `__getattr__` lazy-loading pattern
  - Cached lazy-loaded YAML functions in `globals()` to avoid repeated `__getattr__` calls
  - 2 regression tests to prevent recurrence

## [0.16.0] - 2026-02-09

### Added

- **EnumEvidenceTier for Evidence-Gated Promotion** [OMN-2043] (#494): New enum in the pattern_learning domain with four ordered tiers for threshold-based promotion decisions
  - Tiers: `UNMEASURED < OBSERVED < MEASURED < VERIFIED` with numeric weight ordering
  - Supports comparison operators (`__lt__`, `__le__`, `__gt__`, `__ge__`) via weight-based ordering
  - Coerces string operands to enum values for correct comparison semantics (avoids lexicographic ordering bugs)

- **Event Typing and Schema Versioning for ModelEventEnvelope** [OMN-2035] (#493): Three new optional fields for explicit event dispatch and payload version tracking
  - `event_type: str | None` — dot-path routing key for event dispatch
  - `payload_type: str | None` — Pydantic model class name for deserialization
  - `payload_schema_version: ModelSemVer | None` — payload schema version for evolution
  - Bumped `envelope_version` to 2.1.0; updated `TypedDictEventEnvelopeDict` and `to_dict_lazy()`
  - Full backwards compatibility — all fields default to `None`

- **Interface Models for ModelTicketContract** [OMN-1971] (#490): Integrate interface definitions into ticket contracts for mock-based parallel development
  - Added `interfaces_provided` and `interfaces_consumed` fields to `ModelTicketContract`
  - New `VERIFY_INTERFACE` variant in `EnumVerificationKind`
  - Updated `__repr__` to include interface counts for debugging

- **ModelInterfaceProvided/Consumed and Supporting Enums** [OMN-1968] (#489): Frozen Pydantic models for interface definitions enabling mock-based parallel development
  - `ModelInterfaceProvided` and `ModelInterfaceConsumed` — typed interface contracts
  - 4 new enums: `EnumInterfaceKind`, `EnumMockStrategy`, `EnumDefinitionFormat`, `EnumInterfaceSurface`
  - `EnumDefinitionLocation` replaces `Literal["inline", "file_ref"]` per enum policy
  - Cross-field validation: `definition_ref` required when `definition_location=FILE_REF`
  - 69 unit tests covering immutability, validation, and YAML round-trip

- **Phase 3 Cross-Repo Validation Rules** [OMN-1906] (#488): Four new AST-based validation rules with fingerprinting for baseline tracking
  - `validator_duplicate_protocols` — detect protocol classes defined in multiple files
  - `validator_partition_key` — require explicit `partition_key` in topic configs
  - `validator_observability` — flag `print()`, raw `logging.getLogger()`, and `logging.Logger()` instantiation
  - `validator_async_policy` — flag blocking calls (`time.sleep`, `requests`, `subprocess`) in async functions
  - Shared `util_exclusion.py` for DRY path exclusion logic across all rules
  - Wrapper suppression for `asyncio.to_thread()` and similar async wrappers
  - Nested async function scope handling to prevent double-reporting
  - Regex validation on `topic_config_pattern` at config parse time
  - 243+ tests across all four rules

### Fixed

- **Remove Legacy dev.omnimemory Topic Constants** [OMN-1554] (#492): Delete hardcoded `dev.omnimemory.*` module-level constants using the old naming convention
  - Removed `INTENT_STORED_EVENT`, `INTENT_QUERY_REQUESTED_EVENT`, `INTENT_QUERY_RESPONSE_EVENT`
  - Replaced event_type defaults with ONEX-standard `onex.omnimemory.*` identifiers
  - Updated all tests to use inline string values

- **Harden ModelTicketContract** [OMN-1819] (#491): UTC enforcement, type guards, and iterable support for ticket contracts
  - UTC timezone enforcement validator for `created_at`/`updated_at` on deserialization
  - Type guard in `assert_action_allowed()` for non-str/non-enum inputs
  - Extended `research_notes` property to handle arbitrary iterables (tuple, set, generator)
  - Documented fingerprint collision resistance (16-char hex = ~2^32 birthday bound)
  - 19 new tests covering UTC enforcement, unexpected types, and iterable handling

### Refactored

- **Consolidate Error Models into ModelErrorDetails** [OMN-1765] (#486): Single canonical error model replacing three overlapping implementations
  - Moved `ModelErrorDetails` from `models/services/` to `models/core/`
  - Removed `ModelBaseError` (simple string-based) and `ModelOnexErrorDetails` (medium complexity)
  - Migrated `ModelLogEntry` and `ModelValidateMessage` from inheritance to direct fields
  - Features: generic `TContext` support, inner error chaining, recovery info (`retry_after`, `suggestions`), correlation tracking, thread-safe immutability (`frozen=True`)
  - Added `model_config` with `frozen=True` and `extra="forbid"` to `ModelBaseResult`, `ModelValidateResult`, `ModelServiceConfiguration`
  - Resolved circular import chains in `models/services/` via relative imports

## [0.15.0] - 2026-02-05

### Added

- **Field Projection Validation for DB Repository Contracts** [OMN-1790]: Validate that SELECT column lists match contract field definitions
  - Ensures type safety between SQL queries and return type specifications
  - Detects mismatches between projected fields and model_ref schemas

- **Positional Parameter Support ($N) for DB Repository Contracts** [OMN-1789]: Extend parameter validation to support PostgreSQL-style positional parameters
  - Supports `$1`, `$2`, etc. alongside existing named `:param` syntax
  - Full validation for parameter count and ordering

- **CTE and Subquery Table Extraction** [OMN-1791]: Enhanced SQL parsing for complex queries
  - Extract table references from Common Table Expressions (CTEs)
  - Parse subqueries to identify all accessed tables
  - Improves table access control validation accuracy

- **Cross-Repo Validation Orchestrator** [OMN-1776]: Unified orchestration layer for running validators across multiple repositories
  - Centralized configuration for multi-repo validation runs
  - Aggregated reporting across repository boundaries
  - Support for parallel validation execution

- **Pydantic Models for Agent YAML Schema Validation** [OMN-1902]: Type-safe models for validating agent configuration files
  - `ModelAgentYamlSchema` - Root schema for agent YAML files
  - Validation for agent identity, capabilities, and routing configuration
  - Integration with existing contract validation infrastructure

## [0.14.0] - 2026-02-04

### Added

- **ModelMessageEnvelope with Cryptographic Signing** [OMN-1898]: Runtime-gateway-centric message envelope with Ed25519 signatures and Blake3 payload hashing for secure inter-service communication
  - `ModelMessageEnvelope[T]` - Generic signed envelope for typed payloads
  - `ModelEnvelopeSignature` - Signature metadata with algorithm and timestamp
  - `ModelEmitterIdentity` - Component identity for observability
  - `ProtocolKeyProvider` - Interface for key storage backends
  - Crypto utilities: Blake3 hasher, Ed25519 signer, FileKeyProvider

- **Phase 1 Cross-Repo Validators** [OMN-1775]: Three new validation rules to prevent "2am incidents"
  - `rule_error_taxonomy` - Enforces canonical error module usage, proper ModelOnexError inheritance, and error_code requirements
  - `rule_contract_schema` - Validates contract YAML files have required fields (contract_version, node_type, name, description)
  - `rule_topic_naming` - Enforces ONEX topic naming conventions, detects invalid formats and hardcoded topic strings

- **Injection Metrics Event Contracts** [OMN-1901]: Shared event payload models and topic constants for injection effectiveness metrics
  - `ModelContextUtilizationPayload` - Track context usage effectiveness
  - `ModelAgentMatchPayload` - Track agent routing accuracy
  - `ModelLatencyBreakdownPayload` - Detailed timing breakdown
  - Topic constants for `context-utilization`, `agent-match`, and `latency-breakdown` events

### Changed

- **ProtocolEventBusSubscriber** now uses `node_identity` for consistent subscriber identification
- **Architecture Handshakes**: Updated omniclaude constraints to v0.2.0

## [0.13.1] - 2026-02-02

### Added

- **TypedDictPatternStorageMetadata** [OMN-1780]: Strongly-typed TypedDict for pattern storage metadata
  - Replaces `dict[str, Any]` with typed structure for `tags`, `learning_context`, and `additional_attributes`
  - Ensures JSON serialization compatibility with string-only additional attributes

## [0.13.0] - 2026-02-02

### Added

- **TicketContract Model for Contract-Driven Ticket Execution** [OMN-1807]: New models for defining ticket workflows with requirements, verification steps, and gates
  - `ModelTicketContract` - Main contract model with phases, requirements, and gates
  - `ModelClarifyingQuestion` - Structured questions for requirement gathering
  - `ModelRequirement` - Individual requirement with verification steps
  - `ModelVerificationStep` - Step-by-step verification with expected outcomes
  - `ModelGate` - Approval gates between ticket phases
  - `EnumTicketPhase`, `EnumTicketAction`, `EnumTicketStepStatus`, `EnumVerificationKind`, `EnumGateKind` - Supporting enums
  - `LinearClientProtocol`, `FileSystemProtocol`, `NotificationProtocol` - DI protocols for external integrations

- **Architecture Constraint Maps** [OMN-1832]: Declarative architecture handshakes for 8 active repositories
  - YAML-based constraint definitions for cross-repo architectural rules
  - Install script for syncing constraints across repositories

- **CI Enforcement for Version Verification** [OMN-1862]: Automated version checking in CI pipelines
  - Shell scripts for verifying version consistency
  - Pre-commit hooks for local validation

### Documentation

- **CLAUDE.md Rewrite**: Comprehensive documentation overhaul with declarative node patterns and four-node architecture guide

## [0.12.0] - 2026-02-01

### Added

- **Contract-Driven DB Repository Schema and Validators** [OMN-1782]: Implement v1 of contract-driven database repository system for type-safe SQL operations
  - `ModelDbParam` - Parameter definition with type-based constraints
  - `ModelDbReturn` - Return type specification (model_ref + many cardinality)
  - `ModelDbSafetyPolicy` - Opt-in flags for dangerous operations (DELETE/UPDATE without WHERE)
  - `ModelDbOperation` - SQL operation with mode, params, returns, safety_policy
  - `ModelDbRepositoryContract` - Full repository contract with table access control
  - Validators: `validator_db_structural`, `validator_db_sql_safety`, `validator_db_table_access`, `validator_db_deterministic`, `validator_db_params`
  - Shared `_sql_utils.py` module with `normalize_sql()` and `strip_sql_strings()`
  - Named parameters only (`:param` style), fail-closed on CTEs/subqueries
  - 40+ unit tests and example YAML contract

- **Adoption Enablement for Cross-Repo Validators** [OMN-1774]: Phase 0.5 implementation enabling incremental adoption through fingerprinting, baselines, and policy inheritance
  - Violation fingerprinting: deterministic SHA-256 based `hash(rule_id, file_path, symbol)[:16]`
  - Baseline mode: `--baseline-write` and `--baseline-enforce` CLI flags
  - JSON output hardening: counts by severity, rule_id, suppressed status
  - Policy inheritance: `extends` field with shallow merge semantics
  - `util_fingerprint.py` - Deterministic fingerprint generation
  - `model_baseline_*.py` - Pydantic models for baseline YAML format
  - `baseline_io.py` - YAML read/write utilities
  - Baseline behavior: baselined violations become INFO/suppressed, new violations fail
  - O(1) fingerprint lookup via cached frozenset in `ModelViolationBaseline`
  - 70+ new tests covering all new functionality

## [0.11.0] - 2026-01-31

### Added

- **Contract-Driven Zero-Code Node Base Classes** [OMN-1731]: Enable fully declarative ONEX nodes where `class NodeMyEffect(NodeEffect): pass` works entirely from contract YAML
  - `ModelProtocolDependency` - Protocol dependency declaration with name, protocol path, required flag, bind_as alias, and lazy_import support
  - `ModelProtocolsNamespace` - Immutable namespace for `self.protocols.<name>` access pattern
  - `resolver_handler` - Resolves handlers from `module:callable` import paths with caching
  - `resolver_protocol_dependency` - Resolves protocol dependencies from container with validation
  - `ModelHandlerRoutingEntry` - Added `callable` and `lazy_import` fields for contract-driven handler dispatch
  - `ModelContractBase` - Added `protocol_dependencies` list with duplicate detection
  - `ModelHandlerRoutingSubcontract` - Added `validate_zero_code_requirements()` method
  - `NodeCoreBase` - Added `protocols` namespace and `_resolve_protocol_dependencies()` method
  - `NodeEffect` - Auto-loads effect_subcontract, dispatches via `default_handler`
  - `NodeCompute` - Dispatches via `default_handler` with generic support
  - `get_contract_attr()` utility for dict/Pydantic model attribute access
  - New error code `PROTOCOL_CONFIGURATION_ERROR` (126) for DI failures
  - 52 new invariant tests covering contract completeness, protocol resolution, namespace immutability

- **Cross-Repository Conformance Validators** [OMN-1771]: Contract-driven validation system for enforcing code placement, import boundaries, and repo conventions
  - `ModelValidationPolicyContract` - Policy contract model for validation rules
  - `ModelValidationDiscoveryConfig` - Discovery configuration for finding files to validate
  - `ModelRuleConfigs` - Rule configuration models (repo_boundaries, forbidden_imports)
  - `ModelViolationWaiver` - Waiver model for exempting known violations
  - Validation engine with CLI support (JSON/text output)
  - AST-based import graph scanner
  - Synthetic test fixtures (fake_core, fake_infra, fake_app)
  - 55 unit tests
  - Design: Validators in core (fixed rule IDs), policies in each repo (thresholds, allowlists)

## [0.10.2] - 2026-01-31

### Added

- **Request-Response Schema Support** [OMN-1760]: Added `request_response` field to `ModelEventBusSubcontract`
  - `ModelRequestResponseConfig` - Top-level config containing list of request-response instances
  - `ModelRequestResponseInstance` - Individual pattern config with request topic, reply topics, timeout, consumer group mode
  - `ModelReplyTopics` - Completed/failed topic suffix pairs with ONEX naming validation
  - `ModelCorrelationConfig` - Correlation ID location config (body/headers)
  - All topic suffixes validated against ONEX naming convention
  - Non-empty instances list enforced to prevent silent no-op configurations
  - `auto_offset_reset` defaults to `"earliest"` to prevent race conditions in request-response patterns
  - Comprehensive test coverage (871 lines, 70+ test cases)
  - Enables contract-driven request-response wiring in `omnibase_infra` (OMN-1742)

## [0.10.1] - 2026-01-31

### Added

- **Kafka Import Guard** [OMN-1745]: Extended CI guard to block direct Kafka imports
  - Renamed `validate-no-listener-apis.py` → `validate-no-kafka-listener-apis.py`
  - Added patterns for: `AIOKafkaConsumer`, `KafkaConsumer`, `AIOKafkaProducer`, `KafkaProducer`
  - Added `# kafka-import-ok:` bypass marker (alongside existing `# listener-api-ok:`)
  - Updated pre-commit hook id and name to reflect expanded scope
  - Provides defense-in-depth: Level 1 guards listener APIs, Level 2 guards raw Kafka imports
  - Enforces ARCH-002: "Runtime owns all Kafka plumbing"

## [0.10.0] - 2026-01-31

### Breaking Changes

- **Removed Listener Management from MixinEventBus** [OMN-1747]: Listener/consumer lifecycle code removed from `omnibase_core`
  - ⚠️ **BREAKING**: `MixinEventListener` mixin removed entirely
  - ⚠️ **BREAKING**: `ModelEventBusListenerHandle` model removed
  - ⚠️ **BREAKING**: `ProtocolEventBusListener` protocol removed
  - ⚠️ **BREAKING**: `MixinEventBus` methods removed:
    - `start_event_listener()`, `stop_event_listener()`, `_event_listener_loop()`
    - `get_event_patterns()`, `get_completion_event_type()`, `bind_contract_path()`
    - `_create_event_handler()`, `_event_to_input_state()`, `_get_input_state_class()`
  - **Migration**: Use `EventBusSubcontractWiring` in `omnibase_infra` for Kafka consumer lifecycle
  - Enforces architectural invariant: "infra owns Kafka plumbing, core provides publish-only abstractions"

### Removed

- `src/omnibase_core/mixins/mixin_event_listener.py` - Entire file (1,117 lines)
- `src/omnibase_core/models/event_bus/model_event_bus_listener_handle.py` - Entire file (470 lines)
- `src/omnibase_core/protocols/event_bus/protocol_event_bus_listener.py` - Entire file (33 lines)
- `tests/unit/mixins/test_mixin_event_listener.py` - 30 listener tests
- `tests/unit/models/event_bus/test_model_event_bus_listener_handle.py` - 62 listener tests
- 25 listener-related tests from `test_mixin_event_bus.py`

### Changed

- **MixinEventBus refactored** to publish-only (40% smaller: 1,977 → 1,200 lines)
  - Retained: `publish_event()`, `publish_completion_event()`, `apublish_completion_event()`
  - Retained: `bind_event_bus()`, `bind_registry()`, `bind_node_name()`
  - Retained: `_get_event_bus()`, `_require_event_bus()`, `_has_event_bus()`
- `model_service_effect.py`: Removed `stop_event_listener()` fallback in cleanup
- `mixin_tool_execution.py`: Updated docstrings to remove listener references
- `conftest.py`: Removed dead listener thread cleanup code

### Added

- **CI Guard** [OMN-1747]: Pre-commit hook to prevent listener API reintroduction
  - `scripts/validation/validate-no-listener-apis.py` - Validation script
  - `.pre-commit-config.yaml` - New `validate-no-listener-apis` hook
  - Guards against: `start_event_listener`, `stop_event_listener`, `_event_listener_loop`, `ModelEventBusListenerHandle`

## [0.9.11] - 2026-01-30

### Added

- **Intent Classification Keywords Field** [OMN-1728]: Added `keywords: list[str]` field to `ModelIntentClassificationOutput`
  - Captures keywords/features that contributed to the classification decision
  - Uses `default_factory=list` for safe mutable default
  - Unblocks `ProtocolIntentGraph` conformance (OMN-1729, OMN-1730)

## [0.9.10] - 2026-01-30

### Added

- **Claude Code Tool Execution Content Model** [OMN-1701]: Added `ModelToolExecutionContent` and `EnumClaudeCodeToolName` for pattern learning
  - `EnumClaudeCodeToolName`: 26 Claude Code tool names with classification helpers
  - `ModelToolExecutionContent`: Tool execution capture model with dual-field pattern
  - Helper methods: `is_file_operation()`, `is_search_operation()`, `is_execution_tool()`, etc.
  - Privacy fields: `is_content_redacted`, `redaction_policy_version`
  - MCP tool prefix handling (`mcp__*` pattern)

## [0.9.9] - 2026-01-29

### Added

- **Platform Baseline Topic Suffix Constants** [OMN-1652]: Added individual topic suffix constants for cross-repository imports
  - `TOPIC_SUFFIX_CONTRACT_REGISTERED` - Contract registration event topic suffix
  - `TOPIC_SUFFIX_CONTRACT_DEREGISTERED` - Contract deregistration event topic suffix
  - `TOPIC_SUFFIX_NODE_HEARTBEAT` - Node heartbeat event topic suffix
  - `PLATFORM_BASELINE_TOPIC_SUFFIXES` tuple refactored to use individual constants
  - Enables `omnibase_infra` to import canonical topic strings from core

## [0.9.8] - 2026-01-29

### Added

- **Contract Publisher Mixin** [OMN-1655]: Added `MixinContractPublisher` for nodes to publish contracts on startup
  - `publish_contract(contract_path)` - Reads YAML, computes SHA256 hash, publishes `ModelContractRegisteredEvent`
  - `publish_deregistration(reason)` - Publishes `ModelContractDeregisteredEvent` for graceful shutdown
  - `start_heartbeat(interval_seconds)` - Background task emitting `ModelNodeHeartbeatEvent`
  - Uses `ProtocolEventBusPublisher` from core (not SPI) for proper layering
  - Enables dynamic contract discovery via Kafka event bus

## [0.9.7] - 2026-01-27

### Added

- **Tool Failure Pattern Classification** [OMN-1609]: Added `EnumPatternKind.TOOL_FAILURE` for classifying tool failure patterns
  - Distinct from `TOOL_USAGE` (success patterns vs failure patterns)
  - Covers recurring failures, failure sequences, recovery patterns, etc.

- **Tool Execution Model** [OMN-1608]: Added `ModelToolExecution` to intelligence models
  - Frozen Pydantic model for structured tool execution data
  - Computed `directory` property derived from file path
  - Supports pattern extraction for tool usage analysis

- **Contract Infrastructure Extensions** [OMN-1588]: Added ONEX infrastructure extension fields to `ModelContractBase`
  - `yaml_consumed_events`, `yaml_published_events`, `handler_routing` fields
  - New `ModelConsumedEventEntry` and `ModelPublishedEventEntry` models
  - Field validators normalize string lists to typed entries
  - Enables contract-driven infrastructure configuration
  - Added `TypedDictConsumedEventEntry` and `TypedDictPublishedEventEntry` for strong typing

## [0.9.6] - 2026-01-26

### Added

- **Pattern Extraction Models** [OMN-1587]: Added models for intelligence pattern extraction
  - Canonical Pydantic models for code pattern analysis results
  - Support for extracting and representing code patterns from analysis pipelines

## [0.9.5] - 2026-01-26

### Added

- **Topic Suffix Validation Utilities** [OMN-1537]: Added canonical topic suffix validation for contract-driven topic declaration
  - `validate_topic_suffix()`, `parse_topic_suffix()`, `compose_full_topic()` utilities
  - `ModelTopicSuffixParts` and `ModelTopicValidationResult` models
  - `publish_topics`/`subscribe_topics` fields in `ModelEventBusSubcontract`
  - `ModelTopicMeta` for future schema reference support
  - `EnumTopicType.DLQ` for Dead Letter Queue topic type
  - Topic suffix format: `onex.{kind}.{producer}.{event-name}.v{n}`

### Documentation

- **Operation Bindings DSL** [OMN-1517]: Added comprehensive documentation for the `operation_bindings` declarative handler wiring schema

## [0.9.4] - 2026-01-25

### Added

- **Intent Storage Event Models** [OMN-1513]: Added canonical event models for the intent storage pipeline
  - `ModelEventPayloadBase`: Base class for embedded payloads (frozen, metadata-free)
  - `ModelIntentStoredEvent`: Emitted after intent storage to graph database
  - `ModelIntentQueryRequestedEvent`: Dashboard queries (distribution/session/recent)
  - `ModelIntentQueryResponseEvent`: Response with intent records
  - `IntentRecordPayload`: Lightweight intent record for query responses

- **Operation Bindings Schema** [OMN-1410]: Added `operation_bindings` schema for declarative handler wiring

- **Session and Intent Classification Models** [OMN-1489] [OMN-1490]: Added session snapshot and intent classification models

- **Claude Code Hook Input Types** [OMN-1474]: Added integration types for Claude Code hooks

### Changed

- **Handler Contract Refactor** [OMN-1465]: Renamed `handler_kind` to `node_archetype` in handler contracts for clarity

## [0.9.1] - 2026-01-22

### Fixed

- **PEP 561 Compliance**: Added `py.typed` marker file for proper type checking support in downstream packages

### Changed

- **Contract Version Enforcement** [OMN-1436]: Strict enforcement of `contract_version` field - removed deprecated `version` field fallback in handler contracts

## [0.9.0] - 2026-01-21

### ⚠️ BREAKING CHANGES

#### Contract Version Field Rename [OMN-1431]

**`ModelContractBase.version` renamed to `contract_version`** to align with ONEX specification naming conventions.

| Before (v0.8.x) | After (v0.9.0) |
|-----------------|----------------|
| `contract.version` | `contract.contract_version` |
| YAML: `version:` | YAML: `contract_version:` |

**New field added:** `node_version: ModelSemVer | None` for tracking node implementation versions separately from contract schema versions.

**Migration:**
```python
# Before (v0.8.x)
contract = ModelContractCompute(
    name="my_node",
    version=ModelSemVer(major=1, minor=0, patch=0),
    ...
)

# After (v0.9.0)
contract = ModelContractCompute(
    name="my_node",
    contract_version=ModelSemVer(major=1, minor=0, patch=0),
    node_version=ModelSemVer(major=1, minor=0, patch=0),  # Optional
    ...
)
```

**Note:** Other models retain their own `version` fields (not renamed):
- `ModelProfileReference.version`
- `ModelValidatorSubcontract.version`

#### Handler Contract Version Field Migration [OMN-1436]

**`ModelHandlerContract.version` migrated to `contract_version: ModelSemVer`** with strict enforcement. Handler contracts now require the structured `contract_version` field instead of the legacy string-based `version` field.

| Before (v0.8.x) | After (v0.9.0) |
|-----------------|----------------|
| `version: "1.0.0"` | `contract_version: {major: 1, minor: 0, patch: 0}` |
| `ModelHandlerContract(version="1.0.0")` | `ModelHandlerContract(contract_version=ModelSemVer(...))` |

**YAML Migration:**
```yaml
# Before (v0.8.x)
name: my_handler
version: "1.0.0"
handler_kind: compute

# After (v0.9.0)
name: my_handler
contract_version:
  major: 1
  minor: 0
  patch: 0
handler_kind: compute
```

**Python Migration:**
```python
# Before (v0.8.x)
from omnibase_core.models.runtime.model_handler_contract import ModelHandlerContract

contract = ModelHandlerContract(
    name="my_handler",
    version="1.0.0",
    handler_kind=EnumHandlerKind.COMPUTE,
)

# After (v0.9.0)
from omnibase_core.models.runtime.model_handler_contract import ModelHandlerContract
from omnibase_core.models.primitives.model_semver import ModelSemVer

contract = ModelHandlerContract(
    name="my_handler",
    contract_version=ModelSemVer(major=1, minor=0, patch=0),
    handler_kind=EnumHandlerKind.COMPUTE,
)
```

**Validation:** Strict contracts (those inheriting from `ModelContractBase` with `is_strict_contract()` returning `True`) now require `contract_version` to be explicitly set. Loading a handler contract YAML without `contract_version` will raise a validation error.

### Added

- **Guardrail Validator**: `ValidatorContractLinter` now rejects YAML contracts using deprecated `version:` field, enforcing migration to `contract_version:`

## [0.8.0] - 2026-01-17

### Added

- **Metrics Emission Models**: New models for observability metrics emission with cardinality policies [OMN-1367]

### Changed

- **Header Cleanup**: Removed legacy SPDX headers from omnibase_core codebase [OMN-1360]

## [0.7.0] - 2026-01-15

### ⚠️ BREAKING CHANGES

This release contains significant breaking changes to enum and type alias organization. These changes improve type safety, eliminate duplication, and establish canonical patterns for the codebase.

#### Status Enum Consolidation [OMN-1310]

**57+ overlapping status enums consolidated into 4 canonical enums.** No backwards compatibility - duplicates removed outright.

| Canonical Enum | Values |
|----------------|--------|
| `EnumExecutionStatus` | PENDING, RUNNING, COMPLETED, SUCCESS, FAILED, SKIPPED, CANCELLED, TIMEOUT, PARTIAL |
| `EnumOperationStatus` | SUCCESS, FAILED, IN_PROGRESS, CANCELLED, PENDING, TIMEOUT |
| `EnumWorkflowStatus` | PENDING, RUNNING, COMPLETED, FAILED, CANCELLED, PAUSED |
| `EnumHealthStatus` | HEALTHY, DEGRADED, UNHEALTHY, CRITICAL, UNKNOWN, WARNING, UNREACHABLE, AVAILABLE, UNAVAILABLE, ERROR, INITIALIZING, DISPOSING |

**Deleted Enum Files:**
- `enum_execution.py` (consolidated into EnumExecutionStatus)
- `enum_execution_status_v2.py` (consolidated into EnumExecutionStatus)
- `enum_health_status_type.py` (consolidated into EnumHealthStatus)
- `enum_node_health_status.py` (consolidated into EnumHealthStatus)

**Migration Guide:**
```python
# Before (v0.6.x)
from omnibase_core.enums import EnumExecution, EnumHealthStatusType

status = EnumExecution.RUNNING
health = EnumHealthStatusType.HEALTHY

# After (v0.7.0)
from omnibase_core.enums import EnumExecutionStatus, EnumHealthStatus

status = EnumExecutionStatus.RUNNING
health = EnumHealthStatus.HEALTHY
```

#### Severity Enum Canonicalization [OMN-1311]

**5 severity enums merged into canonical `EnumSeverity`.** This establishes a single source of truth for severity levels across the codebase.

| Action | Enums |
|--------|-------|
| **Merged into EnumSeverity** | `EnumValidationSeverity`, `EnumInvariantSeverity`, `EnumViolationSeverity` |
| **Removed (unused)** | `EnumErrorSeverity`, old `EnumSeverity` (orphaned with wrong values) |
| **Kept separate (documented exceptions)** | `EnumSeverityLevel` (RFC 5424 logging), `EnumImpactSeverity` (business domain) |

**Canonical EnumSeverity Values:** DEBUG, INFO, WARNING, ERROR, CRITICAL, FATAL

**Migration Guide:**
```python
# Before (v0.6.x)
from omnibase_core.enums import EnumValidationSeverity, EnumInvariantSeverity

severity = EnumValidationSeverity.ERROR
invariant_sev = EnumInvariantSeverity.CRITICAL

# After (v0.7.0)
from omnibase_core.enums import EnumSeverity

severity = EnumSeverity.ERROR
invariant_sev = EnumSeverity.CRITICAL
```

#### Literal Type Aliases Replaced with Canonical Enums [OMN-1308]

**11 Literal type definitions removed** from `protocols/base/__init__.py` and replaced with proper enums.

**New Enums Created:**

| Enum | Values |
|------|--------|
| `EnumServiceLifecycle` | singleton, transient, scoped, pooled, lazy, eager |
| `EnumInjectionScope` | request, session, thread, process, global, custom |
| `EnumServiceResolutionStatus` | resolved, failed, circular_dependency, etc. |
| `EnumPipelineValidationMode` | strict, lenient, smoke, regression, integration |
| `EnumStepType` | compute, effect, reducer, orchestrator, parallel, custom |
| `EnumRegistrationStatus` | registered, unregistered, failed, pending, etc. |

**Migration Guide:**
```python
# Before (v0.6.x) - Using Literal types
from omnibase_core.protocols.base import ServiceLifecycle
lifecycle: ServiceLifecycle = "singleton"

# After (v0.7.0) - Using enums
from omnibase_core.enums import EnumServiceLifecycle
lifecycle = EnumServiceLifecycle.SINGLETON
```

#### Type Alias Consolidation [OMN-1294]

Duplicate type aliases consolidated to eliminate redundancy:

| Old Type Alias | New Type Alias | Reason |
|----------------|----------------|--------|
| `LogContextValue` | `EnvValue` | Identical semantics |
| `PayloadDataValue` | `CliValue \| None` | Equivalent type |
| `ParameterValue` | `QueryParameterValue` | Renamed (different semantics) |
| `ConfigValue` | `ScalarConfigValue` | Renamed (narrower semantics) |

#### Enum Member Casing Standardization [OMN-1307]

**All enum members must use UPPER_SNAKE_CASE.** `EnumFileStatus` members renamed from lowercase to UPPER_SNAKE_CASE. String values unchanged for backward compatibility in serialized data.

```python
# Before (v0.6.x)
class EnumFileStatus(str, Enum):
    pending = "pending"
    processing = "processing"

# After (v0.7.0)
class EnumFileStatus(str, Enum):
    PENDING = "pending"      # String value unchanged
    PROCESSING = "processing"
```

**Impact:** Code referencing `EnumFileStatus.pending` must change to `EnumFileStatus.PENDING`.

### Added

- **EnumSeverity**: Canonical 6-level severity taxonomy (DEBUG, INFO, WARNING, ERROR, CRITICAL, FATAL) with `StrValueHelper` mixin [OMN-1296]
- **Enum Governance Checker**: `checker_enum_governance.py` for automated enforcement of enum standards [OMN-1296]
- **Enum Member Casing Validator**: `checker_enum_member_casing.py` AST-based validator with pre-commit integration [OMN-1307]
- **Literal Duplication Checker**: `checker_literal_duplication.py` to prevent Literal/Enum duplication [OMN-1308]
- **ModelOmniMemoryContract**: YAML schema for OmniMemory contracts [OMN-1251]
- **ManifestGenerator Callback**: `on_manifest_built` callback hook for pipeline manifest generation [OMN-1203]
- **JSON-Safety Validation**: `ModelPayloadExtension` JSON-safety validation [OMN-1266]
- **Container Public API**: `initialize_service_registry()` public API for container initialization [OMN-1265]
- **Evidence Export Service**: Demo service with renderer refactoring [OMN-1200]
- **ModelMemorySnapshot**: Unified state container for OmniMemory [OMN-1243]
- **Non-Deterministic Effect Classification**: Effect classification system for replay safety [OMN-1147]
- **Pydantic Conventions Validator**: Validator for Pydantic model patterns [OMN-1314]
- **Invariant Violation Report Model**: Demo model for invariant violations [OMN-1206]
- **Error Handling Patterns**: Standardized error handling patterns with decorators [OMN-1299]
- **Support Assistant Handler**: Demo handler for model evaluation [OMN-1201]
- **ADR-013 Status Taxonomy**: Architecture decision record for status enum taxonomy [OMN-1312]

### Changed

- **File Headers**: Unified file headers across omnibase_core codebase [OMN-1337]
- **Type Annotations**: Modernized to PEP 604 union syntax (`X | Y` instead of `Union[X, Y]`) [OMN-1300]
- **Pydantic Patterns**: Standardized Pydantic model patterns across codebase [OMN-1301]
- **File/Class Naming**: Fixed naming convention violations [OMN-1298]

### Fixed

- **EnumValidationSeverity Import**: Removed broken import that blocked all enum imports [#397]
- **Status String References**: Replaced hardcoded status strings with enum references [OMN-1309]

### Refactored

- **Type Ignore Comments**: Reduced `type: ignore` comments by 35% through proper typing [OMN-1073]
- **AI Slop Patterns**: Removed AI-generated boilerplate patterns from codebase [OMN-1297]

## [0.6.6] - 2026-01-12

### Added

- **EnumHandlerRoutingStrategy** (OMN-1295): Added enum for handler routing strategies replacing Literal type, improving type safety and IDE support
- **Replay Safety Enforcement** (OMN-1150): Implemented replay safety enforcement for non-deterministic effects with audit trail and UUID injection services
- **Baseline Health Report Models** (OMN-1198): Added baseline health report models, performance metrics, and stability calculator utilities
- **Execution Detail View Models** (OMN-1197): Added execution detail view models and consolidated comparison models into replay module

### Changed

- **MixinHandlerRouting**: Updated to use EnumHandlerRoutingStrategy enum with proper type annotations
- **ModelHandlerRoutingSubcontract**: Optimized duplicate routing_key validation to use set instead of list

## [0.6.5] - 2026-01-12

### Changed

- Version bump from 0.6.4 to 0.6.5 for release tagging

## [0.6.4] - 2026-01-11

### Added

- **MixinHandlerRouting** (OMN-1293): Added contract-driven handler routing mixin for flexible handler resolution
- **Correlation ID Propagation** (OMN-601): Implemented correlation_id propagation across all intents for improved traceability
- **ModelExecutionProfile Extensions** (OMN-1292): Extended ModelExecutionProfile and ModelExecutionConflict for ProtocolConstraintValidator

## [0.6.3] - 2026-01-08

### Changed

- Version bump from 0.6.2 to 0.6.3 for release tagging

## [0.6.2] - 2026-01-06

### Fixed

- **Version Mismatch**: Fixed package version inconsistency where PyPI 0.6.1 was published with `__version__ = "0.5.3"` in source code. Both `pyproject.toml` and `__init__.py` now correctly report 0.6.2.

## [0.6.1] - 2026-01-06

### Added

- **Contract CLI Tooling** (OMN-1129): Added CLI commands for contract management and validation
- **ModelHandlerPackaging** (OMN-1119): Added secure handler distribution with cryptographic signing and verification
- **Diff Rendering & Storage Hooks** (OMN-1149): Added explainability output support with diff rendering capabilities
- **Handler Contract Protocols** (OMN-1164): Migrated handler contract protocols from SPI to Core
- **ModelProjectionResult** (OMN-1233): Added projection result model for projection operations

## [0.6.0] - 2026-01-05

### ⚠️ BREAKING CHANGES

#### ModelHandlerBehaviorDescriptor Renamed to ModelHandlerBehavior [OMN-1117]

The `ModelHandlerBehaviorDescriptor` class has been renamed to `ModelHandlerBehavior`. The backwards compatibility shim (`model_handler_behavior_descriptor.py`) and alias have been **removed**.

**Impact**:
- Code importing `ModelHandlerBehaviorDescriptor` will raise `ImportError`
- Code importing from `model_handler_behavior_descriptor` will raise `ImportError`

**Migration Guide**:

```python
# Before (v0.3.x)
from omnibase_core.models.runtime.model_handler_behavior_descriptor import (
    ModelHandlerBehaviorDescriptor,
)
contract = ModelHandlerContract(
    descriptor=ModelHandlerBehaviorDescriptor(handler_kind="compute", ...),
    ...
)

# After (v0.4.0+)
from omnibase_core.models.runtime.model_handler_behavior import (
    ModelHandlerBehavior,
)
contract = ModelHandlerContract(
    descriptor=ModelHandlerBehavior(handler_kind="compute", ...),
    ...
)
```

**Quick Migration**:
```bash
# Find affected imports
grep -rn "ModelHandlerBehaviorDescriptor\|model_handler_behavior_descriptor" --include="*.py"

# Replace in files (Linux/macOS)
find . -name "*.py" -exec sed -i 's/ModelHandlerBehaviorDescriptor/ModelHandlerBehavior/g' {} \;
find . -name "*.py" -exec sed -i 's/model_handler_behavior_descriptor/model_handler_behavior/g' {} \;
```

#### File Renames for Directory Prefix Naming Conventions [OMN-1222]

Files across 4 directories have been renamed to follow consistent directory prefix naming conventions. **Direct module imports to old paths will fail with `ModuleNotFoundError`**.

**Affected Directories**:

| Directory | Old Pattern | New Pattern | Files Affected |
|-----------|-------------|-------------|----------------|
| `logging/` | `*.py` | `logging_*.py` | 4 files |
| `runtime/` | `*.py` | `runtime_*.py` | 5 files |
| `services/registry/` | `registry_*.py` | `service_registry_*.py` | 2 files |
| `validation/` | `*.py` | `validator_*.py` | 5 files |

**Impact**:
- Direct module imports like `from omnibase_core.runtime.file_registry import FileRegistry` will fail
- Package-level imports still work: `from omnibase_core.runtime import FileRegistry`
- Class renames in `services/registry/` have deprecation warnings via `__getattr__`

**Key File Renames**:

```text
# logging/
core_logging.py          → logging_core.py
emit.py                  → logging_emit.py
pydantic_json_encoder.py → logging_pydantic_encoder.py
structured.py            → logging_structured.py

# runtime/
envelope_router.py       → runtime_envelope_router.py
file_registry.py         → runtime_file_registry.py
handler_registry.py      → runtime_handler_registry.py
message_dispatch_engine.py → runtime_message_dispatch.py
protocol_node_runtime.py → runtime_protocol_node.py

# services/registry/
registry_capability.py   → service_registry_capability.py
registry_provider.py     → service_registry_provider.py

# validation/
architecture.py          → validator_architecture.py
cli.py                   → validator_cli.py
contracts.py             → validator_contracts.py
patterns.py              → validator_patterns.py
types.py                 → validator_types.py
```

**Migration Guide**:

```python
# Before (v0.3.x) - Direct module imports
from omnibase_core.runtime.file_registry import FileRegistry
from omnibase_core.validation.architecture import validate_architecture_directory
from omnibase_core.logging.structured import emit_log_event_sync

# After (v0.4.0+) - Use package-level imports (recommended)
from omnibase_core.runtime import FileRegistry
from omnibase_core.validation import validate_architecture_directory
from omnibase_core.logging import emit_log_event_sync

# After (v0.4.0+) - Or use new module paths directly
from omnibase_core.runtime.runtime_file_registry import FileRegistry
from omnibase_core.validation.validator_architecture import validate_architecture_directory
from omnibase_core.logging.logging_structured import emit_log_event_sync
```

**Quick Migration**:
```bash
# Find affected imports
grep -rn "from omnibase_core\.\(logging\|runtime\|validation\)\.\(core_logging\|emit\|structured\|file_registry\|envelope_router\|architecture\|cli\|contracts\|patterns\|types\)" --include="*.py"

# Recommended: Update to package-level imports for future compatibility
```

#### Hook Typing Enforcement Enabled by Default [OMN-1157]

The default value of `BuilderExecutionPlan.enforce_hook_typing` has been changed from `False` to `True`. This is a **fail-fast behavior change** that affects code building execution plans with typed hooks.

**Impact**:
- **Before (v0.5.x)**: Hook type mismatches produced `ModelValidationWarning` objects in the warnings list
- **After (v0.6.x)**: Hook type mismatches raise `HookTypeMismatchError` immediately during `build()`

**Rationale**:
- Fail-fast behavior catches type mismatches during development rather than allowing silent degradation
- Type validation errors in production indicate configuration issues that should be addressed, not ignored
- This aligns with ONEX's philosophy of explicit, type-safe contracts

**Migration Guide**:

1. **Recommended**: Ensure all hooks have correct `handler_type_category` values:
   ```python
   from omnibase_core.pipeline import BuilderExecutionPlan, ModelPipelineHook
   from omnibase_core.enums import EnumHandlerTypeCategory

   # Typed hook - must match contract_category
   hook = ModelPipelineHook(
       hook_id="my-compute-hook",
       phase="execute",
       callable_ref="app.hooks.compute",
       handler_type_category=EnumHandlerTypeCategory.COMPUTE,  # Must match builder
   )

   # Generic hook - passes for any contract (no handler_type_category)
   generic_hook = ModelPipelineHook(
       hook_id="my-generic-hook",
       phase="execute",
       callable_ref="app.hooks.generic",
       # No handler_type_category = generic, passes all type validation
   )

   # Build with type enforcement (now the default)
   builder = BuilderExecutionPlan(
       registry=registry,
       contract_category=EnumHandlerTypeCategory.COMPUTE,
       # enforce_hook_typing=True is now the default
   )
   plan, warnings = builder.build()  # Raises HookTypeMismatchError on type mismatch
   ```

2. **For gradual migration**, explicitly disable enforcement:
   ```python
   # Opt-in to warning-only mode for backwards compatibility
   builder = BuilderExecutionPlan(
       registry=registry,
       contract_category=EnumHandlerTypeCategory.COMPUTE,
       enforce_hook_typing=False,  # Explicit opt-out to warning-only mode
   )
   plan, warnings = builder.build()

   # Check warnings for type mismatches
   for warning in warnings:
       if warning.code == "HOOK_TYPE_MISMATCH":
           logger.warning(f"Type mismatch: {warning.message}")
   ```

3. **Identify affected code** by searching for `BuilderExecutionPlan` usage:
   ```bash
   # Find all usages
   grep -rn "BuilderExecutionPlan" --include="*.py"

   # Find usages that might rely on warning-only behavior
   grep -rn "enforce_hook_typing" --include="*.py"
   ```

**Quick Migration Checklist**:
- [ ] Review all `BuilderExecutionPlan` instantiations
- [ ] Ensure typed hooks have correct `handler_type_category` matching `contract_category`
- [ ] Use generic hooks (no `handler_type_category`) for hooks that should work with any contract
- [ ] Add `enforce_hook_typing=False` to builders that need gradual migration
- [ ] Run tests to verify no `HookTypeMismatchError` is raised unexpectedly

#### Workflow Contract Model Hardening [OMN-654]

The following workflow contract models now enforce **immutability** (`frozen=True`) and **field validation**:

| Model | Changes Applied |
|-------|-----------------|
| `ModelWorkflowDefinition` | Added `frozen=True`, `extra="ignore"` (v1.0.5 Fix 54) |
| `ModelWorkflowDefinitionMetadata` | Added `frozen=True`, `extra="forbid"` |
| `ModelWorkflowStep` | Added `extra="forbid"` (already had `frozen=True`) |
| `ModelCoordinationRules` | Added `frozen=True`, `extra="ignore"` (v1.0.5 Fix 54) |
| `ModelExecutionGraph` | Added `frozen=True`, `extra="ignore"` (v1.0.5 Fix 54) |
| `ModelWorkflowNode` | Added `frozen=True`, `extra="ignore"` (v1.0.5 Fix 54) |

**v1.0.5 Fix 54: Reserved Fields Governance** - Models with `extra="ignore"` implement reserved fields governance for forward compatibility. "Reserved fields" are fields defined in newer schema versions that older code does not recognize. This governance policy ensures:

- **No validation errors** when newer schema versions include reserved (unrecognized) fields
- **Fields are dropped** during model construction - reserved fields are discarded, NOT preserved in round-trip serialization
- **Graceful degradation** allows older code to process newer data formats without crashing

This policy ensures that workflow contracts from future ONEX versions can be parsed by current code without errors, even if reserved fields are not yet understood by the current schema version.

**Impact**:
- Code that **mutates these models after creation** will now raise `pydantic.ValidationError`
- For `extra="forbid"` models: Code that **passes unknown fields** will raise `pydantic.ValidationError`
- For `extra="ignore"` models (v1.0.5 Fix 54): Reserved fields are dropped during construction - they are discarded, not preserved in round-trip serialization

**Thread Safety Benefits**:

Since these models are now `frozen=True`, they are **inherently thread-safe for reads**:

| Operation | Thread-Safe? | Notes |
|-----------|-------------|-------|
| Reading model attributes | Yes | No mutation possible after creation |
| Sharing models across threads | Yes | Immutable objects are safe to share |
| Creating modified copies with `model_copy()` | Yes | Creates new instance, no shared mutable state |
| Passing models between async tasks | Yes | No race conditions on immutable data |

This aligns with the ONEX thread safety model documented in [docs/guides/THREADING.md](docs/guides/THREADING.md). Workflow contract models now join other frozen models (like `ModelComputeInput`, `ModelReducerInput`, etc.) in being safe for concurrent access without synchronization.

**Migration Guide**:

#### 1. Direct Mutation to Immutable Copies

```python
# Before (v0.3.x) - Direct mutation was possible
workflow = ModelWorkflowDefinition(...)
workflow.version = new_version  # ❌ Now raises pydantic.ValidationError

# After (v0.4.0+) - Use model_copy() for modifications
workflow = ModelWorkflowDefinition(...)
updated_workflow = workflow.model_copy(update={"version": new_version})  # ✅ Correct

# Multiple field updates in one call
updated = original.model_copy(update={
    "version": new_version,
    "workflow_metadata": new_metadata,
})
```

#### 2. Handling Extra Fields

Models have different behaviors based on their `extra=` policy:

**For `extra="forbid"` models** (e.g., `ModelWorkflowDefinitionMetadata`, `ModelWorkflowStep`):
```python
# Extra fields raise pydantic.ValidationError
metadata = ModelWorkflowDefinitionMetadata(
    version=version,
    workflow_name="my-workflow",
    workflow_version=workflow_version,
    custom_field="value"  # ❌ Raises pydantic.ValidationError
)
```

**For `extra="ignore"` models** (v1.0.5 Fix 54: Reserved Fields Governance):
```python
# Reserved fields are silently dropped during construction
definition = ModelWorkflowDefinition(
    version=version,
    workflow_metadata=metadata,
    execution_graph=graph,
    future_field="value"  # ⚠️ Silently dropped - NOT preserved in round-trip
)
# definition.future_field does not exist - the field was discarded
```

**Best practice**: Use designated extension fields rather than relying on extra field behavior:
```python
# Use proper extension mechanisms instead of arbitrary fields
metadata = ModelWorkflowDefinitionMetadata(
    version=version,
    workflow_name="my-workflow",
    workflow_version=workflow_version,
    description="Description with any custom info you need",
)
```

#### 3. Nested Model Updates

```python
# For deeply nested updates, rebuild from the inside out:
original = ModelWorkflowDefinition(...)

# Update nested metadata
new_metadata = original.workflow_metadata.model_copy(
    update={"description": "Updated description"}
)

# Create new definition with updated metadata
updated = original.model_copy(update={"workflow_metadata": new_metadata})
```

#### 4. Pattern for Workflow Builders

```python
# If you have a builder pattern that relied on mutation, convert to accumulation:

# Before (v0.3.x) - Mutable builder
class WorkflowBuilder:
    def __init__(self):
        self.workflow = ModelWorkflowDefinition(...)

    def set_timeout(self, ms: int):
        self.workflow.timeout_ms = ms  # ❌ No longer works

# After (v0.4.0+) - Immutable builder with accumulated state
class WorkflowBuilder:
    def __init__(self):
        self._updates: dict[str, Any] = {}
        self._base_config = {...}

    def set_timeout(self, ms: int) -> "WorkflowBuilder":
        self._updates["timeout_ms"] = ms
        return self

    def build(self) -> ModelWorkflowDefinition:
        return ModelWorkflowDefinition(**{**self._base_config, **self._updates})
```

#### 5. Testing Code Updates

```python
# Tests that mutated models need updating:

# Before (v0.3.x)
def test_workflow_processing():
    workflow = create_workflow()
    workflow.status = "completed"  # ❌ No longer works
    assert workflow.status == "completed"

# After (v0.4.0+)
def test_workflow_processing():
    workflow = create_workflow()
    completed_workflow = workflow.model_copy(update={"status": "completed"})
    assert completed_workflow.status == "completed"
```

**Quick Migration Checklist**:

- [ ] Search codebase for direct attribute assignment to workflow contract models
- [ ] Replace direct mutations with `model_copy(update={...})` calls
- [ ] Remove any extra fields being passed to model constructors
- [ ] Update builder patterns to accumulate state rather than mutate
- [ ] Run tests to verify `pydantic.ValidationError` is not raised unexpectedly
- [ ] Verify thread safety requirements are met (frozen models are now safe to share)

#### Model Relocations and Naming Conventions [OMN-1067]

Several model classes have been relocated from `mixins/` and `runtime/` to `models/` to follow ONEX file location conventions. Classes have been renamed from `Mixin*` to `Model*` prefix to reflect that they are Pydantic data models, not behavioral mixins.

**Model Relocations**:

| Old Location | New Location |
|--------------|--------------|
| `mixins/mixin_log_data.py` | `models/mixins/model_log_data.py` |
| `mixins/mixin_node_introspection_data.py` | `models/mixins/model_node_introspection_data.py` |
| `mixins/mixin_completion_data.py` | `models/mixins/model_completion_data.py` |
| `runtime/runtime_node_instance.py` | `models/runtime/model_runtime_node_instance.py` |
| `models/context/model_error_context.py` | `models/context/model_error_metadata.py` |

**Class Renames**:

| Old Name | New Name |
|----------|----------|
| `MixinLogData` | `ModelLogData` |
| `MixinNodeIntrospectionData` | `ModelNodeIntrospectionData` |
| `MixinCompletionData` | `ModelCompletionData` |
| `RuntimeNodeInstance` | `ModelRuntimeNodeInstance` |
| `ModelErrorContext` | `ModelErrorMetadata` |

**Migration Guide**:

```python
# Before (v0.3.x)
from omnibase_core.mixins import MixinLogData, MixinCompletionData
from omnibase_core.runtime import RuntimeNodeInstance
from omnibase_core.models.context import ModelErrorContext

log_data = MixinLogData(...)
completion = MixinCompletionData(...)
node = RuntimeNodeInstance(...)
error = ModelErrorContext(...)

# After (v0.4.0+)
from omnibase_core.models.mixins import ModelLogData, ModelCompletionData
from omnibase_core.models.runtime import ModelRuntimeNodeInstance
from omnibase_core.models.context import ModelErrorMetadata

log_data = ModelLogData(...)
completion = ModelCompletionData(...)
node = ModelRuntimeNodeInstance(...)
error = ModelErrorMetadata(...)
```

#### UUID Type Strengthening [OMN-1067]

Several ID fields that were previously typed as `str` are now typed as `UUID`. Pydantic 2.11+ automatically coerces UUID strings to `UUID` objects, so string inputs are still accepted.

**Affected Fields**:

| Model | Field | Old Type | New Type |
|-------|-------|----------|----------|
| `ModelErrorMetadata` | `stack_trace_id` | `str \| None` | `UUID \| None` |
| `ModelCheckpointMetadata` | `parent_checkpoint_id` | `str \| None` | `UUID \| None` |
| `ModelSessionContext` | `session_id` | `str \| None` | `UUID \| None` |

**Migration Guide**:

```python
# Both of these work - Pydantic auto-converts strings:
metadata = ModelErrorMetadata(stack_trace_id="12345678-1234-5678-1234-567812345678")
metadata = ModelErrorMetadata(stack_trace_id=UUID("12345678-1234-5678-1234-567812345678"))

# Reading the field returns a UUID object:
assert isinstance(metadata.stack_trace_id, UUID)  # True

# For string comparisons, convert explicitly:
if str(metadata.stack_trace_id) == expected_uuid_string:
    ...
```

**Note**: Invalid UUID strings will now raise `ValidationError` during model construction rather than being accepted as arbitrary strings.

#### Security: Deprecated MD5/SHA-1 Hash Algorithms [OMN-699]

`ModelSessionAffinity` now deprecates MD5 and SHA-1 hash algorithms due to known cryptographic weaknesses. These algorithms are auto-converted to SHA-256 with a `DeprecationWarning`. **Support will be fully removed in v0.6.0.**

**Impact**:
- Configurations with `hash_algorithm: "md5"` or `hash_algorithm: "sha1"` will emit `DeprecationWarning` and auto-convert to SHA-256
- Running with `-W error::DeprecationWarning` will convert these to errors (useful for CI/CD validation)
- Only SHA-256, SHA-384, and SHA-512 are recommended for new configurations
- **v0.6.0**: MD5/SHA-1 will be fully removed and raise `pydantic.ValidationError`

**Migration**:
```python
# Current behavior (v0.5.0) - Deprecation warning + auto-conversion
affinity = ModelSessionAffinity(hash_algorithm="md5")   # ⚠️ Warning, converts to sha256
affinity = ModelSessionAffinity(hash_algorithm="sha1")  # ⚠️ Warning, converts to sha256

# Recommended - Use secure algorithms (no warnings)
affinity = ModelSessionAffinity(hash_algorithm="sha256")  # ✅ Default, recommended
affinity = ModelSessionAffinity(hash_algorithm="sha384")  # ✅ Stronger
affinity = ModelSessionAffinity(hash_algorithm="sha512")  # ✅ Strongest
```

**Recommendation**: Update configurations to use SHA-256 (default) before v0.6.0. Use SHA-384 or SHA-512 for high-security environments.

#### MixinEventBus STRICT_BINDING_MODE Default Changed [OMN-1156]

The default value of `MixinEventBus.STRICT_BINDING_MODE` has been changed from `False` to `True`. This is a **fail-fast behavior change** that affects code calling `bind_*()` methods after the mixin is "in use" (after `start_event_listener()` or publish operations).

**Impact**:
- **Before (v0.4.x)**: `bind_*()` calls after mixin is in use emitted a WARNING log
- **After (v0.5.x)**: `bind_*()` calls after mixin is in use raise `ModelOnexError` with `error_code=INVALID_STATE`

**Rationale**:
- Fail-fast behavior catches thread-unsafe patterns in production before they cause subtle race conditions
- Warnings can be missed in CI/CD pipelines and logs, but errors are immediately visible
- This aligns with ONEX thread safety principles documented in [docs/guides/THREADING.md](docs/guides/THREADING.md)

**Migration Guide**:

1. **Recommended**: Ensure all `bind_*()` calls occur in `__init__` before the mixin is shared across threads:
   ```python
   class MyNode(MixinEventBus[InputT, OutputT]):
       def __init__(self, event_bus: ProtocolEventBus):
           super().__init__()
           # All binding must happen in __init__ BEFORE any publish or listener operations
           self.bind_event_bus(event_bus)
           self.bind_node_name("my_node")
   ```

2. **For legacy code** that cannot be immediately refactored, disable strict mode by subclassing:
   ```python
   from typing import ClassVar

   class MyLegacyNode(MixinEventBus[InputT, OutputT]):
       STRICT_BINDING_MODE: ClassVar[bool] = False  # Opt-out to warning-only behavior
   ```

3. **Identify affected code** by searching for patterns where `bind_*()` is called after `start_event_listener()` or `publish_*()`:
   ```bash
   # Find potential issues
   grep -rn "start_event_listener" --include="*.py" | xargs grep -l "bind_"
   grep -rn "publish_event\|publish_completion_event" --include="*.py" | xargs grep -l "bind_"
   ```

**Quick Migration Checklist**:
- [ ] Review all usages of `MixinEventBus` subclasses
- [ ] Ensure `bind_*()` methods are called in `__init__` before any publish/listener operations
- [ ] Add `STRICT_BINDING_MODE = False` to legacy classes that cannot be immediately fixed
- [ ] Run tests to verify no `ModelOnexError` with `INVALID_STATE` is raised unexpectedly

#### MixinEventBus Architecture Refactoring [OMN-1081]

`MixinEventBus` has been refactored to use composition with dedicated data models, separating state management from behavior. This change improves thread safety, eliminates MRO conflicts, and enables proper serialization of runtime state.

##### Architectural Changes

| Aspect | Before (v0.4.x) | After (v0.5.x) |
|--------|-----------------|----------------|
| **State Storage** | Direct instance attributes | Composition with `ModelEventBusRuntimeState` |
| **Listener Handle** | Untyped threading objects | `ModelEventBusListenerHandle` with thread safety |
| **Initialization** | `__init__` method required | Lazy state accessors (no `__init__`) |
| **Binding** | Implicit attribute assignment | Explicit binding methods required |
| **Thread Safety** | Not guaranteed | Lock-protected operations in `ModelEventBusListenerHandle` |

##### New Data Models

| Model | Purpose | Thread Safety |
|-------|---------|---------------|
| `ModelEventBusRuntimeState` | Serializable binding state (node_name, contract_path, is_bound) | NOT thread-safe (mutable) |
| `ModelEventBusListenerHandle` | Listener lifecycle management (thread, stop_event, subscriptions) | Thread-safe (lock-protected) |

##### Breaking Changes

1. **Explicit Binding Required**: You must call binding methods before publishing events:
   - `bind_event_bus(event_bus)` - Bind an event bus instance
   - `bind_registry(registry)` - Bind a registry with event_bus property
   - `bind_contract_path(path)` - Set contract path for event patterns
   - `bind_node_name(name)` - Set node name for logging/events

2. **Lazy State Initialization**: State is created on first access, not in `__init__`.

3. **Fail-Fast Semantics**: Publishing without binding raises `ModelOnexError` immediately.

4. **Input Validation on Binding**: `bind_node_name()` and `bind_contract_path()` now raise `ModelOnexError` for invalid input (empty strings, None values, whitespace-only strings). Previously these might have been silently accepted.

5. **Binding Reset via reset() Method**: To clear a binding, use `ModelEventBusRuntimeState.reset()` instead of binding an empty string. Empty string binding now raises `ModelOnexError`.

6. **Runtime Misuse Detection**: Binding methods now emit warnings if called after the object has been shared across threads (detected via binding lock state). This helps catch thread-safety violations early.

##### New Features

1. **Generic Type Parameters**: `MixinEventBus[InputStateT, OutputStateT]` now supports generic type parameters for type-safe event processing. This enables IDE autocomplete and static type checking for event payloads.

2. **Thread-Safe stop() and dispose()**: `ModelEventBusListenerHandle.stop()` and `dispose_event_bus_resources()` are now fully thread-safe with lock-protected operations. Multiple threads can safely call these methods concurrently (idempotent).

3. **Runtime Misuse Detection**: The mixin now detects and warns about common misuse patterns:
   - Binding after object is shared across threads
   - Publishing without proper binding
   - Listener lifecycle violations

4. **Serializable Runtime State**: `ModelEventBusRuntimeState` is a Pydantic model that can be serialized/deserialized, enabling state persistence and debugging.

##### Deprecation Timeline

| Version | Status | Changes |
|---------|--------|---------|
| **v0.5.x** | Current | Backwards compatibility via `hasattr` fallbacks for lazy initialization |
| **v1.0** | Planned | Remove `hasattr` fallbacks; require explicit `bind_*()` calls in `__init__` |
| **v1.0** | Planned | Standardize `ProtocolEventBus` to require `publish_async()`, `subscribe()`, `unsubscribe()` |

All legacy patterns marked with `TODO(v1.0)` comments in the source code will be cleaned up in v1.0.

##### Migration Guide

###### 1. Update Initialization Pattern

```python
# Before (v0.4.x) - Implicit initialization
class MyNode(NodeCompute, MixinEventBus):
    def __init__(self, container: ModelONEXContainer):
        super().__init__(container)
        self.event_bus = container.get_service("ProtocolEventBus")
        self.node_name = "my_node"  # Direct attribute access
        self.contract_path = "/path/to/contract.yaml"

# After (v0.5.x) - Explicit binding
class MyNode(NodeCompute, MixinEventBus[MyInputState, MyOutputState]):
    def __init__(self, container: ModelONEXContainer):
        super().__init__(container)
        # Use explicit binding methods
        self.bind_event_bus(container.get_service("ProtocolEventBus"))
        self.bind_node_name("my_node")
        self.bind_contract_path("/path/to/contract.yaml")
```

###### 2. Update Event Bus Access

```python
# Before (v0.4.x) - Direct attribute access
if hasattr(self, "event_bus") and self.event_bus:
    self.event_bus.publish(event)

# After (v0.5.x) - Use provided methods
if self._has_event_bus():
    self.publish_completion_event(event_type, data)
# OR for required access:
bus = self._require_event_bus()  # Raises ModelOnexError if not bound
```

###### 3. Update Listener Management

```python
# Before (v0.4.x) - Manual thread management
class MyNode(MixinEventBus):
    def start_listening(self):
        self._listener_thread = threading.Thread(target=self._listen_loop)
        self._stop_event = threading.Event()
        self._listener_thread.start()

    def stop_listening(self):
        self._stop_event.set()
        self._listener_thread.join()

# After (v0.5.x) - Use ModelEventBusListenerHandle
class MyNode(MixinEventBus[MyInputState, MyOutputState]):
    def start_listening(self):
        # Returns thread-safe handle
        self._handle = self.start_event_listener()

    def stop_listening(self):
        # Uses lock-protected stop with timeout
        success = self.stop_event_listener(self._handle)
        if not success:
            self.logger.warning("Listener did not stop within timeout")
```

###### 4. Update State Access

```python
# Before (v0.4.x) - Direct attribute access
node_name = self.node_name
contract_path = self.contract_path

# After (v0.5.x) - Use accessor methods
node_name = self.get_node_name()  # Falls back to class name if not bound
# Contract path is accessed internally by get_event_patterns()
```

###### 5. Clearing Bindings

```python
# Before (v0.4.x) - Empty string binding (no longer works)
self.bind_node_name("")  # ❌ Now raises ModelOnexError

# After (v0.5.x) - Use reset() method
self._event_bus_state.reset()  # ✅ Clears all bindings properly

# Or for selective reset, create a new state:
from omnibase_core.models.mixins import ModelEventBusRuntimeState
self._event_bus_state = ModelEventBusRuntimeState()  # Fresh state
```

###### 6. Handle Input Validation Errors

```python
# Before (v0.4.x) - Invalid input might be silently accepted
self.bind_node_name(None)  # Might have worked (undefined behavior)
self.bind_contract_path("  ")  # Whitespace might have been accepted

# After (v0.5.x) - Invalid input raises ModelOnexError
from omnibase_core.errors import ModelOnexError

try:
    self.bind_node_name(user_provided_name)
except ModelOnexError as e:
    # Handle invalid input - empty, None, or whitespace-only
    self.logger.warning(f"Invalid node name: {e}")
    self.bind_node_name(self.__class__.__name__)  # Use fallback
```

##### Thread Safety Notes

| Method/Operation | Thread-Safe? | Notes |
|-----------------|--------------|-------|
| `bind_event_bus()` | **NO** | Must be called during `__init__` |
| `bind_registry()` | **NO** | Must be called during `__init__` |
| `bind_contract_path()` | **NO** | Must be called during `__init__` |
| `bind_node_name()` | **NO** | Must be called during `__init__` |
| `stop_event_listener()` | **YES** | Lock-protected, idempotent |
| `dispose_event_bus_resources()` | **YES** | Lock-protected, idempotent |

**Important**: All `bind_*()` methods are **NOT thread-safe** and must be called during object initialization (`__init__`), before the object is shared across threads. Once bound, the event bus can be safely used from multiple threads.

- `ModelEventBusListenerHandle.stop()` uses a three-phase lock pattern:
  1. **Phase 1 (lock held)**: Capture references, set stop signal
  2. **Phase 2 (lock released)**: Wait for thread with timeout
  3. **Phase 3 (lock held)**: Clean up subscriptions, update state

- Multiple threads can safely call `stop()` concurrently (idempotent)
- Default stop timeout is 5.0 seconds (configurable)
- Listener threads are daemon threads (auto-terminate on main exit)

##### Resource Cleanup

```python
# Call on shutdown to clean up all event bus resources
self.dispose_event_bus_resources()
```

##### Quick Migration Checklist

- [ ] Replace direct `self.event_bus = ...` with `self.bind_event_bus(...)`
- [ ] Replace direct `self.node_name = ...` with `self.bind_node_name(...)`
- [ ] Replace direct `self.contract_path = ...` with `self.bind_contract_path(...)`
- [ ] Update any `hasattr(self, "event_bus")` checks to use `self._has_event_bus()`
- [ ] Add `Generic[InputStateT, OutputStateT]` type parameters if using typed event processing
- [ ] Update listener management to use `start_event_listener()` / `stop_event_listener()`
- [ ] Add `dispose_event_bus_resources()` call to shutdown/cleanup methods
- [ ] Review thread safety requirements - `ModelEventBusListenerHandle` is now thread-safe
- [ ] **NEW**: Ensure all `bind_*()` calls are in `__init__` before object is shared across threads
- [ ] **NEW**: Add error handling for `bind_node_name()` and `bind_contract_path()` which now validate input
- [ ] **NEW**: Replace empty string binding with `ModelEventBusRuntimeState.reset()` to clear bindings
- [ ] **NEW**: Watch for binding lock warnings indicating thread-safety violations

#### Invariant Validation Returns Detailed Violation Model [OMN-1207]

Invariant validation methods that previously returned `bool` or raised generic exceptions now return `ModelInvariantViolationDetail` on failure. This provides structured debugging information but changes the return type signature.

**Impact**:
- Code checking invariant validation results via boolean comparison may need updates
- Exception handlers catching generic `ValidationError` should now handle `ModelInvariantViolationDetail`

**Migration Guide**:

```python
# Before (v0.5.x) - Boolean return or exception
result = validate_invariant(data)
if not result:
    logger.error("Invariant failed")

# After (v0.6.x) - Structured violation detail
from omnibase_core.models.validation import ModelInvariantViolationDetail

result = validate_invariant(data)
if isinstance(result, ModelInvariantViolationDetail):
    logger.error(f"Invariant failed: {result.violation_type} - {result.message}")
    logger.debug(f"Context: {result.context}")
```

### Added

#### Replay & Trace Infrastructure

- **Deterministic Replay Infrastructure**: Foundation for deterministic execution replay and validation [OMN-1116]
- **ModelExecutionComparison**: Comparison model for baseline vs replay execution validation [OMN-1194]
- **ModelEvidenceSummary**: Evidence summary model for aggregating corpus replay results [OMN-1195]
- **ModelExecutionCorpus**: Corpus model for organizing and managing replay test sets [OMN-1202]
- **Configuration Override Injection**: Configuration override injection for A/B testing scenarios [OMN-1205]
- **Execution Trace Models**: Models for capturing and storing execution traces [OMN-1208]
- **ServiceTraceRecording**: Service for recording execution traces to storage backends [OMN-1209]

#### Contract System

- **AST-Based Transport Import Validator**: Static analysis validator for transport layer import compliance [OMN-1039]
- **YAML !include Directive Support**: Support for !include directives in YAML contract files for modular composition [OMN-1047]
- **Handler Contract Model & YAML Schema**: ModelHandlerContract with comprehensive YAML schema for handler definitions [OMN-1117]
- **ModelContractPatch**: Patch model for incremental contract modifications with validation [OMN-1126]
- **Typed Contract Merge Engine**: Type-safe engine for merging contract definitions with conflict resolution [OMN-1127]
- **Contract Validation Pipeline**: Multi-stage pipeline for validating contracts through configurable stages [OMN-1128]
- **Contract Validation Event Schema**: Event schema for contract validation lifecycle events [OMN-1146]
- **Contract Diff Model**: Model for computing and representing patch-level diffs between contracts [OMN-1148]
- **Validation Pipeline Event Emission**: Event emission hooks for contract validation pipeline stages [OMN-1151]

#### Validation & Invariants

- **Invariant Definition Models**: Models for defining and configuring invariant rules [OMN-1192]
- **ServiceInvariantEvaluator**: Service for evaluating invariants against runtime state [OMN-1193]
- **ModelInvariantViolationDetail**: Structured violation detail model for debugging invariant failures [OMN-1207]

#### Pipeline & Execution

- **ExecutionResolver**: Resolver for mapping handler contracts to executable implementations [OMN-1106]
- **Runtime Execution Sequencing Model**: Model for defining execution ordering and dependencies [OMN-1108]
- **Pure Handler Conversions**: Utilities for converting between handler types with type safety [OMN-1112]
- **Execution Manifest Generation**: Generator for creating execution manifests from pipeline definitions [OMN-1113]
- **Pipeline Runner & Hook Registry**: Pipeline execution engine with pluggable hook registry [OMN-1114]

#### Observability

- **Dispatch ID Propagation**: Correlation ID propagation through dispatch chains for distributed tracing [OMN-972]
- **Prometheus Metrics Backend**: Prometheus-compatible metrics export backend [OMN-1188]
- **Redis Cache Backend**: Redis-backed caching implementation for distributed deployments [OMN-1188]

#### Security

- **AES-256-GCM Encryption**: Symmetric encryption support using AES-256-GCM for sensitive data [OMN-1077]

#### Handler & Capability System

- **Handler Enums**: Enumeration types for handler classification and behavior [OMN-1085]
- **Handler Descriptors**: Descriptor models for handler metadata and configuration [OMN-1086]
- **Handler Metadata Models**: Comprehensive metadata models for handler introspection [OMN-1121]
- **Capability Models**: Models for defining and advertising node capabilities [OMN-1122]
- **Capability Factories**: Factory classes for capability instantiation and configuration [OMN-1123]
- **Handler Contract Extensions**: Extended contract fields for advanced handler scenarios [OMN-1124]
- **Handler Type Categories**: Category-based handler classification system [OMN-1125]
- **Capability Dependencies**: Dependency declaration and resolution for capabilities [OMN-1152]
- **Capability Providers**: Provider abstraction for capability implementations [OMN-1153]
- **Capability Requirements**: Requirement specification for capability consumers [OMN-1154]
- **Capability Requirement Bindings**: Binding mechanism connecting requirements to providers [OMN-1155]
- **MixinEventBus Strict Binding Mode**: Fail-fast binding validation for event bus mixins [OMN-1156]
- **ModelProjectorContract**: Contract model for projection/view definitions [OMN-1166]

#### NodeOrchestrator Compliance

- **v1.0.1 Compliance Fixes**: NodeOrchestrator compliance with ONEX specification v1.0.1 [OMN-658]
- **v1.0.2 Compliance Fixes**: Enhanced orchestration patterns for v1.0.2 specification [OMN-659]
- **v1.0.3 Compliance Fixes**: Workflow coordination improvements for v1.0.3 specification [OMN-660]
- **v1.0.4 Compliance Fixes**: Action lease semantics updates for v1.0.4 specification [OMN-661]
- **v1.0.5 Compliance Fixes**: Final compliance updates for v1.0.5 specification [OMN-662]
- **Node Protocol Definitions**: Protocol definitions for node type contracts [OMN-664]

#### Protocol & Type System

- **Protocol ISP Split**: Interface Segregation Principle refactoring of monolithic protocols [OMN-1016]
- **SemVer 2.0.0 Support**: Full Semantic Versioning 2.0.0 compliance with pre-release and build metadata [OMN-1020]

#### Constants & Configuration

- **Timeout Constants**: Centralized timeout configuration constants for consistency [OMN-1074]
- **Field Limit Constants**: Centralized field size limit constants for validation [OMN-1076]

#### Type Safety Improvements

- **Typed Unions for Models**: Discriminated union types for model hierarchies [OMN-1008]
- **Typed Metadata Models**: Strongly-typed metadata model replacements for dict[str, Any] [OMN-1009]
- **Typed Union Utilities**: Utility functions for working with typed unions [OMN-1013]
- **Typed Context Models**: Strongly-typed context models replacing generic dicts [OMN-1048, OMN-1049, OMN-1050, OMN-1051, OMN-1052, OMN-1053, OMN-1054]
- **Any Type Removal (Errors Module)**: Eliminated dict[str, Any] from error models [OMN-1174]
- **Any Type Removal (Events Module)**: Eliminated dict[str, Any] from event models [OMN-1175]
- **Any Type Removal (Core Module)**: Eliminated dict[str, Any] from core models [OMN-1176]
- **Any Type Removal (Validation Module)**: Eliminated dict[str, Any] from validation models [OMN-1177]
- **Any Type Removal (Registry Module)**: Eliminated dict[str, Any] from registry models [OMN-1178]
- **Any Type Removal (Infrastructure Module)**: Eliminated dict[str, Any] from infrastructure models [OMN-1179]
- **PEP 604 Union Syntax Conversion**: Migrated Optional[X] and Union[X, Y] to X | Y syntax [OMN-1186]

#### Change Management

- **ModelChangeProposal**: Change proposal model for evaluating system changes [OMN-1196]

#### File Naming Conventions

- **Naming Convention Enforcement**: Automated enforcement of directory-based file naming prefixes [OMN-1224]
- **Naming Convention Checker**: Pre-commit checker for file naming compliance [OMN-1225]

### Fixed

- **Bare Except Replacement**: Replaced bare `except:` clauses with specific exception types [OMN-1064]
- **Generic Exception Catches**: Replaced generic `except Exception` with specific exception handling [OMN-1075]
- **Broken get_metadata() Pattern**: Fixed incorrect get_metadata() implementations across node types [OMN-1083]

### Changed

#### Model Relocations and Renames

- **ModelLogData Relocation**: Moved from `mixins/` to `models/mixins/` with Mixin→Model prefix change [OMN-1066]
- **ModelNodeIntrospectionData Relocation**: Moved from `mixins/` to `models/mixins/` with Mixin→Model prefix change [OMN-1067]
- **ModelCompletionData Relocation**: Moved from `mixins/` to `models/mixins/` with Mixin→Model prefix change [OMN-1069]
- **ModelRuntimeNodeInstance Relocation**: Moved from `runtime/` to `models/runtime/` with class rename [OMN-1070]
- **ModelErrorMetadata Rename**: Renamed from ModelErrorContext to ModelErrorMetadata [OMN-1071]

#### MixinEventBus Refactoring

- **MixinEventBus Architecture**: Refactored to composition-based architecture with ModelEventBusRuntimeState and ModelEventBusListenerHandle [OMN-1081]

#### File Naming Convention Renames

- **Logging Module Renames**: Renamed files to follow `logging_*` prefix convention [OMN-1213]
- **Runtime Module Renames**: Renamed files to follow `runtime_*` prefix convention [OMN-1214]
- **Services Registry Renames**: Renamed files to follow `service_registry_*` prefix convention [OMN-1215]
- **Validation Module Renames**: Renamed files to follow `validator_*` prefix convention [OMN-1216]
- **Additional Logging Renames**: Secondary logging file renames for consistency [OMN-1217]
- **Additional Runtime Renames**: Secondary runtime file renames for consistency [OMN-1218]
- **Additional Services Renames**: Secondary services file renames for consistency [OMN-1219]
- **Additional Validation Renames**: Secondary validation file renames for consistency [OMN-1220]
- **Cross-Module Rename Coordination**: Coordinated renames across related modules [OMN-1221]
- **Final Naming Convention Compliance**: Final pass ensuring all files follow conventions [OMN-1222]
- **Import Path Updates**: Updated all import paths to reflect new file names [OMN-1223]

#### Envelope Model Updates

- Renamed `ModelOnexEnvelopeV1` to `ModelOnexEnvelope`
- Renamed fields: `event_id`→`envelope_id`, `source_service`→`source_node`, `event_type`→`operation`
- Added new fields: `causation_id`, `target_node`, `handler_type`, `metadata`, `is_response`, `success`, `error`

## [0.5.5] - 2025-12-20

### Fixed

#### Missing Model Exports [OMN-989]

Exported 4 models from `omnibase_core.models.common` that existed but were not in the public API:

| Model | Purpose |
|-------|---------|
| `ModelTypedMapping` | Type-safe dict replacement for union reduction |
| `ModelValueContainer` | Value container used by ModelTypedMapping |
| `ModelOnexWarning` | Structured warning model |
| `ModelRegistryError` | Canonical registry error model |

**Impact**: Enables `omnibase_infra` to use `ModelTypedMapping` for ~80-100 potential union reductions with proper type safety.

**Canonical Import Paths**:
| Model | Canonical Import | Also Available From |
|-------|-----------------|---------------------|
| `ModelTypedMapping` | `omnibase_core.models.common` | - |
| `ModelValueContainer` | `omnibase_core.models.common` | - |
| `ModelOnexWarning` | `omnibase_core.errors` | `omnibase_core.models.common` |
| `ModelRegistryError` | `omnibase_core.errors` | `omnibase_core.models.common` |

For error/warning models, prefer importing from `omnibase_core.errors` for semantic clarity.

## [0.5.3] - 2025-12-19

### Changed
- Version bump for release tagging (no functional changes from 0.5.2)

## [0.5.2] - 2025-12-19

### Fixed

#### Tech Debt Resolution (P0/P1 Issues)

**Thread Safety Fixes**:
- Fixed circuit breaker race condition in `model_circuit_breaker.py`
  - Added thread-safe locking to all state-modifying operations
  - Created `_unlocked` internal methods to avoid deadlocks
  - Fixed `half_open_requests` counter increment bug

**Timeout Enforcement**:
- Implemented `pipeline_timeout_ms` enforcement in `compute_executor.py`
  - Uses `ThreadPoolExecutor` with timeout for synchronous execution
  - Returns failure result with `TIMEOUT_EXCEEDED` error on timeout
  - Added 8 new tests for timeout behavior

**Workflow Validation**:
- Fixed duplicate step ID validation in `workflow_executor.py`
  - Added validation to detect duplicate step IDs in workflow definitions

### Removed

#### Deprecation Removals (v0.5.0 Announced)
- Removed `computation_type` fallback chain in `node_compute.py` (~70 lines deprecated code)
- Removed `ProtocolRegistryWithBus` alias from `mixins/__init__.py`
- Removed deprecated `JsonSerializable` type alias from `model_onex_common_types.py`

#### Security Hardening
- Removed MD5/SHA-1 hash algorithm support in `model_session_affinity.py`
  - SHA-256 is now the minimum required algorithm
  - Previously deprecated algorithms now raise validation errors

### Changed

#### Documentation Improvements
- Reduced CLAUDE.md from 1145 to 564 lines (51% reduction) while preserving critical information
- Updated README.md import examples to v0.4.0+ patterns
- Updated 10 architecture docs to reflect v0.3.6 dependency inversion (omnibase_spi dependency removal)
- Marked `SPI_PROTOCOL_ADOPTION_ROADMAP.md` as HISTORICAL
- Added timeout thread documentation to `THREADING.md`:
  - Production monitoring for timeout threads
  - Prometheus metrics and warning thresholds
  - `ThreadMonitor` and `TimeoutPool` class implementations
  - Daemon thread lifecycle and resource implications

### Removed
- Deleted stale `README_NODE_REDUCER_TESTS.md` (referenced non-existent file)

## [0.5.1] - 2025-12-18

### Fixed

#### PEP 604 Validator Fix for Dependent Repos [OMN-902]
- Fixed `union_usage_checker.py` to correctly detect PEP 604 union types (`X | Y`) at runtime
- Added `types.UnionType` detection alongside existing `typing.Union` handling
- This fix enables dependent repositories (omnibase_spi, omnibase_nodes, etc.) to use the validator without false positives
- Comprehensive test coverage added for `types.UnionType` detection scenarios

#### UTC Import Fix
- Fixed incorrect UTC import in `model_onex_envelope_v1.py` (was `from datetime import UTC`, now correctly uses `from datetime import timezone`)
- Ensures compatibility across all Python 3.12+ environments

### Testing
- Added 553+ lines of new test coverage for `union_usage_checker.py`
- Comprehensive `types.UnionType` test scenarios including:
  - Direct `X | None` detection
  - Nested unions in generic types
  - Complex union combinations
  - Edge cases with mixed typing styles

### Documentation
- Updated CLAUDE.md with cross-reference to `types.UnionType` behavior differences from `typing.Union`
- Clarified that PEP 604 unions do NOT have `__origin__` accessible via `getattr()` - must use `isinstance(annotation, types.UnionType)` instead

## [0.5.0] - 2025-12-18

### Added

#### Registration Models [OMN-913]
- **ModelRegistrationPayload**: Typed payload for registration intents with comprehensive validation
  - PostgreSQL record storage with `ModelRegistrationRecordBase` type safety
  - Consul service configuration (service ID, name, tags, health checks)
  - Network and deployment metadata (environment, network ID, deployment ID)
  - Field-level validation (min/max lengths, UUID types)
  - Supports flexible Consul health check schema (`dict[str, Any]` for booleans, integers, nested objects)
- **ModelDualRegistrationOutcome**: Registration outcome model with status consistency validation
  - Three status types: `success`, `partial`, `failed`
  - `@model_validator` ensures status consistency with operation flags
  - Error message fields with 2000 character constraints
  - Immutable with thread-safe design (`frozen=True`)
- All models follow ONEX patterns: frozen, extra="forbid", from_attributes=True
- Comprehensive test coverage: 60 tests covering construction, validation, serialization, edge cases

#### Core Intent Discriminated Union [OMN-912]
- Implemented discriminated union pattern for core intents using Pydantic's `Field(discriminator=...)`
- Type-safe intent deserialization with automatic subclass selection
- Enhanced IDE autocomplete and type checking for intent handling

#### Concurrency Testing [OMN-863]
- Comprehensive concurrency tests for all four node types (Effect, Compute, Reducer, Orchestrator)
- Validates thread-safety and parallel execution behavior
- Tests concurrent access patterns and race condition prevention

#### Integration Testing [OMN-864]
- Integration tests for `ModelReducerInput` → `ModelReducerOutput` flows
- End-to-end validation of reducer state management
- FSM transition testing with real workflow scenarios

### Changed

#### Type Safety Improvements [OMN-848]
- Replaced `dict[str, Any]` with strongly typed models across codebase
- Fixed pyright warnings for improved type checking
- Enhanced IDE support and compile-time safety

#### Protocol Standardization [OMN-861]
- Added `ProtocolCircuitBreaker` interface for cross-repository standardization
- Enables consistent circuit breaker patterns across ONEX ecosystem
- Supports dependency injection with protocol-based service resolution

#### Hybrid Type Elimination [OMN-847]
- Eliminated hybrid dict types in favor of pure Pydantic models
- Improved type safety and validation consistency
- Enhanced serialization/deserialization reliability

### Fixed
- Code review feedback from PR #212 (all MAJOR and NITPICK issues resolved)
- Type compliance issues for mypy strict mode (0 errors)
- Pyright basic mode compliance (0 errors, 0 warnings)

### Testing
- Added 60 comprehensive tests for registration models
- Added integration tests for reducer flows
- Added concurrency tests for all node types
- All 12,000+ tests passing across 20 parallel CI splits
- Test execution time: 0.84s for registration models

### Documentation
- Enhanced registration model documentation with usage examples
- Added FSM pattern documentation for discriminated unions
- Updated thread safety guidelines for frozen models

## [0.4.0] - 2025-12-05

> **WARNING**: This is a major release with significant breaking changes. Please review the migration guide before upgrading.

### ⚠️ BREAKING CHANGES

This release implements the **Node Architecture Overhaul**, promoting declarative (FSM/workflow-driven) node implementations as the primary classes. Legacy node implementations have been removed in favor of the new architecture.

#### Node Architecture Overhaul Summary

**What Changed**:
- `NodeReducerDeclarative` → `NodeReducer` (primary FSM-driven implementation)
- `NodeOrchestratorDeclarative` → `NodeOrchestrator` (primary workflow-driven implementation)
- The "Declarative" suffix has been removed - these ARE now the standard implementations
- Legacy implementations (`NodeOrchestratorLegacy`, `NodeReducerLegacy`) have been removed

#### Breaking Changes Summary

| Change | Impact | Migration Effort |
|--------|--------|------------------|
| "Declarative" suffix removed | **HIGH** - Class names changed | Update imports (5 min) |
| Import paths changed | **HIGH** - Old paths removed | Update imports (5 min) |
| Legacy nodes hard deleted | **HIGH** - Must migrate to FSM/workflow patterns (no deprecation period) | See migration guide (30-60 min) |
| FSM-driven NodeReducer is now default | **MEDIUM** - API behavior changes | Review FSM patterns (30 min) |
| Workflow-driven NodeOrchestrator is now default | **MEDIUM** - API behavior changes | Review workflow patterns (30 min) |
| Error recovery patterns changed | **MEDIUM** - Error handling is now declarative | Review error patterns (15 min) |

#### Import Path Changes

**Primary Import Path**:
```python
from omnibase_core.nodes import NodeReducer, NodeOrchestrator, NodeCompute, NodeEffect
```

**Old Declarative Import Path** (no longer works):
```python
# These paths are removed - use omnibase_core.nodes instead
from omnibase_core.infrastructure.nodes.node_reducer_declarative import NodeReducerDeclarative
from omnibase_core.infrastructure.nodes.node_orchestrator_declarative import NodeOrchestratorDeclarative
```

### Changed

#### Node Architecture Overhaul
- **NodeReducer**: Now FSM-driven as the primary implementation (formerly `NodeReducerDeclarative`)
  - Uses `ModelIntent` pattern for pure state machine transitions
  - Intent-based state management separates transition logic from side effects
- **NodeOrchestrator**: Now workflow-driven as the primary implementation (formerly `NodeOrchestratorDeclarative`)
  - Uses `ModelAction` pattern with lease-based single-writer semantics
  - Workflow-driven action definitions with automatic retry and rollback

#### Class Renaming ("Declarative" Suffix Removed)
- `NodeReducerDeclarative` → `NodeReducer`
- `NodeOrchestratorDeclarative` → `NodeOrchestrator`
- All YAML contract-driven configuration is now the default and only approach

### Added

#### Unified Import Surface
- **Single Import Path**: All node types now available from `omnibase_core.nodes`:
  ```python
  from omnibase_core.nodes import (
      NodeCompute,
      NodeEffect,
      NodeReducer,
      NodeOrchestrator,
  )
  ```
- **Input/Output Models**: All node I/O models exported from `omnibase_core.nodes`:
  ```python
  from omnibase_core.nodes import (
      ModelComputeInput,
      ModelComputeOutput,
      ModelReducerInput,
      ModelReducerOutput,
      ModelOrchestratorInput,
      ModelOrchestratorOutput,
      ModelEffectInput,
      ModelEffectOutput,
  )
  ```
- **Public Enums**: Reducer and Orchestrator enums available from `omnibase_core.nodes`

#### Documentation Updates
- **Updated Node Building Guides**: All tutorials reflect v0.4.0 architecture
- **Migration Guide**: New `docs/guides/MIGRATING_TO_DECLARATIVE_NODES.md` for upgrade instructions
- **CLAUDE.md Updates**: Project instructions updated to reflect v0.4.0 patterns

### Removed

#### Legacy Node Implementations (Hard Deletion - No Deprecation Period)
- **`NodeOrchestratorLegacy`**: Fully deleted in favor of workflow-driven `NodeOrchestrator`
- **`NodeReducerLegacy`**: Fully deleted in favor of FSM-driven `NodeReducer`
- **Legacy namespace**: The `omnibase_core.nodes.legacy` namespace does not exist and was never created

#### Legacy Patterns (No Longer Supported)
- **Imperative state management**: Direct state mutation in Reducer nodes (use FSM transitions instead)
- **Custom error handling**: Per-step try/except blocks in Orchestrator nodes (use YAML `failure_recovery_strategy`)
- **Non-lease-based orchestration**: Workflow patterns without `lease_id` and `epoch` (use ModelAction with lease semantics)

#### Old Import Paths
- **Declarative import paths**: `omnibase_core.infrastructure.nodes.node_*_declarative` paths removed
- **Direct infrastructure imports**: Must use `omnibase_core.nodes` for primary implementations

#### Error Recovery Changes (BREAKING)

The error recovery system has been **significantly changed** to align with the declarative architecture. **Existing error handling code will need to be rewritten.**

##### What Changed

| Aspect | Before (v0.3.x) | After (v0.4.0) |
|--------|----------------|----------------|
| **Reducer Error Handling** | `try/except` blocks with direct state mutation | FSM wildcard transitions (`from_state: "*"`) |
| **Orchestrator Error Handling** | Custom Python error handling per step | YAML `failure_recovery_strategy` (retry/skip/abort) |
| **Error State Transitions** | Imperative code sets error state | Declarative FSM transitions via `ModelIntent` |
| **Retry Logic** | Custom retry loops in Python | Lease-based idempotent retries with `lease_id` + `epoch` |

##### Reducer Nodes - Error Recovery Migration

**Before (v0.3.x)** - Imperative error handling:
```python
# Legacy pattern (removed in v0.4.0)
class MyReducer(NodeReducerBase):
    async def process(self, input_data):
        try:
            result = await self.do_work()
            self.state = "completed"
        except Exception as e:
            self.state = "failed"  # Direct state mutation
            self.error = str(e)
            raise
```

**After (v0.4.0)** - Declarative FSM transitions:
```yaml
# In your YAML contract
transitions:
  - from_state: "*"           # Wildcard: catches errors from ANY state
    to_state: failed
    trigger: error_occurred
    actions:
      - action_name: "log_error"
        action_type: "logging"
      - action_name: "emit_failure_event"
        action_type: "event"
```

```python
# Recommended: Use FSM-driven base class
class MyReducer(NodeReducer):
    pass  # Error handling is declarative via YAML
```

##### Orchestrator Nodes - Error Recovery Migration

**Before (v0.3.x)** - Per-step error handling:
```python
# Legacy pattern (removed in v0.4.0)
class MyOrchestrator(NodeOrchestratorBase):
    async def process(self, input_data):
        try:
            await self.step1()
        except Exception:
            await self.retry_step1()  # Custom retry logic
```

**After (v0.4.0)** - Workflow-level failure strategy:
```yaml
# In your YAML contract
coordination_rules:
  failure_recovery_strategy: retry  # Options: retry, skip, abort
  max_retries: 3
  retry_backoff_ms: 1000
```

Actions now include `lease_id` and `epoch` for idempotent retries, preventing duplicate execution.

##### Migration Checklist for Error Handling

- [ ] Remove all `try/except` blocks that mutate state directly in Reducer nodes
- [ ] Add FSM wildcard transitions (`from_state: "*"`) for error handling
- [ ] Remove custom retry loops in Orchestrator nodes
- [ ] Configure `failure_recovery_strategy` in YAML workflow contracts
- [ ] Verify `ModelIntent` emission replaces direct error state mutations
- [ ] Test error recovery paths with the new declarative patterns

---

### Migration Guide (v0.3.x to v0.4.0)

> **Estimated Migration Time**: 30-60 minutes for typical projects. **Full Guide**: See [`docs/guides/MIGRATING_TO_DECLARATIVE_NODES.md`](docs/guides/MIGRATING_TO_DECLARATIVE_NODES.md) for comprehensive migration instructions with complete examples.

#### Quick Migration Checklist

- [ ] Update all node imports to use `omnibase_core.nodes`
- [ ] Replace legacy reducer implementations with `NodeReducer`
- [ ] Replace legacy orchestrator implementations with `NodeOrchestrator`
- [ ] Convert imperative state management to FSM YAML contracts
- [ ] Convert workflow coordination to workflow YAML contracts
- [ ] Update error handling to use declarative patterns
- [ ] Run tests to verify behavior

#### Step 1: Update Imports
```python
# Before (v0.3.x) - Old declarative import paths
from omnibase_core.infrastructure.nodes.node_reducer_declarative import NodeReducerDeclarative

# After (v0.4.0) - Use primary implementation
from omnibase_core.nodes import NodeReducer
```

#### Step 2: Update Class Inheritance
```python
# Before (v0.3.x)
class MyReducer(NodeReducerBase):
    pass

# After (v0.4.0)
class MyReducer(NodeReducer):
    pass
```

#### Step 3: Adopt FSM/Workflow Patterns
- **Reducer nodes**: Implement `ModelIntent` emission instead of direct state updates
- **Orchestrator nodes**: Use `ModelAction` with lease management for coordination
- See [`docs/guides/MIGRATING_TO_DECLARATIVE_NODES.md`](docs/guides/MIGRATING_TO_DECLARATIVE_NODES.md) for detailed examples

#### Step 4: Update Error Handling
```python
# Before (v0.3.x) - Imperative error handling
class MyReducer(NodeReducerBase):
    async def process(self, input_data):
        try:
            result = await self.do_work()
            self.state = "completed"
        except Exception as e:
            self.state = "failed"
            raise

# After (v0.4.0) - Declarative error handling via YAML
# In your contract.yaml:
# transitions:
#   - from_state: "*"
#     to_state: failed
#     trigger: error_occurred
```

---

### ⚠️ Implementation Note: Hard Deletion (Not Soft Deprecation)

> **BREAKING CHANGE**: After reviewing the architecture and confirming that no users currently exist on the legacy node implementations, we pivoted from the originally planned Phase 1 (soft deprecation with warnings) directly to **hard deletion** of legacy nodes.

**Why Hard Deletion Instead of Soft Deprecation?**

1. **No Existing Users**: The legacy `NodeReducerLegacy` and `NodeOrchestratorLegacy` classes had no production usage
2. **Cleaner Codebase**: Removing legacy code entirely eliminates maintenance burden and confusion
3. **Simpler Migration**: Users only need to learn the new patterns, not navigate deprecated APIs
4. **Reduced Risk**: No transition period means no risk of users depending on soon-to-be-removed code

**What This Means for You**:

- Legacy imports (`NodeReducerLegacy`, `NodeOrchestratorLegacy`) will **fail immediately** - no deprecation warnings
- The `omnibase_core.nodes.legacy` namespace **does not exist**
- All nodes must use FSM-driven (`NodeReducer`) or workflow-driven (`NodeOrchestrator`) patterns
- See [`docs/guides/MIGRATING_TO_DECLARATIVE_NODES.md`](docs/guides/MIGRATING_TO_DECLARATIVE_NODES.md) for migration instructions

---

## [0.3.3] - 2025-11-19

### Added

#### Subcontract Models
- **6 New Subcontract Models**: Complete mixin-subcontract architecture with comprehensive Pydantic models
  - `ModelDiscoverySubcontract`: Service discovery configuration with channel validation
  - `ModelEventHandlingSubcontract`: Event subscription and filtering patterns
  - `ModelIntrospectionSubcontract`: Node metadata and capability introspection
  - `ModelLifecycleSubcontract`: Initialization and shutdown lifecycle management
  - `ModelObservabilitySubcontract`: Metrics, logging, and tracing configuration
  - `ModelToolExecutionSubcontract`: Tool and capability execution framework
- **Comprehensive Test Coverage**: 960+ tests for all subcontract models with validation, serialization, and edge case testing

#### Metadata & Manifest Models
- **ModelMixinMetadata**: Declarative mixin metadata with schema validation and subcontract integration
- **ModelDockerComposeManifest**: Docker Compose configuration parsing with port conflict detection and YAML validation
- **Mixin Metadata YAML**: 305-line metadata file (`mixin_metadata.yaml`) with schemas and examples for 5 mixins

#### Documentation Enhancements
- **NODE_CLASS_HIERARCHY.md** (1364 lines): Complete guide to ONEX node class hierarchy with decision trees and migration paths
- **MIXIN_SUBCONTRACT_MAPPING.md** (1104 lines): Comprehensive mapping guide for mixin-to-subcontract relationships
- **TERMINOLOGY_AUDIT_REPORT.md**: Standardization audit for ONEX v2.0 terminology
- **TERMINOLOGY_FIXES_CHECKLIST.md**: Checklist for terminology consistency across codebase

#### Tools & Scripts
- **validate_docs_links.py**: Markdown link validation tool scanning for broken file and anchor references
- **fix_documentation_links.py**: Automated link correction script for predefined fixes

### Changed

#### Error Handling Standardization
- **ModelOnexError Migration**: Renamed `OnexError` → `ModelOnexError` across all documentation and templates (27+ files)
- **Import Path Consolidation**: Standardized import paths to `omnibase_core.models.errors.model_onex_error`
- **correlation_id Best Practices**: Added correlation_id parameter to 19+ error examples for improved traceability

#### Documentation Improvements
- **Pydantic v2 Migration**: Updated 25+ template examples from `@validator` → `@field_validator`
- **Code Example Fixes**: Fixed 91 malformed markdown code fences and 22 inconsistent import paths
- **Template Updates**: Replaced `BaseNodeConfig` with `BaseModel` in 3 template files
- **Processing Time Calculations**: Fixed duration calculation bugs in ENHANCED_NODE_PATTERNS
- **Security Sanitization**: Fixed output propagation in security validation examples

#### Node Base Class Updates
- **Service Wrapper Promotion**: Documentation now recommends `ModelService*` wrappers over legacy `Node*` bases
- **Advanced Patterns Introduction**: Added ONEX v2.0 patterns (ModelIntent for REDUCER, ModelAction for ORCHESTRATOR)

### Fixed

#### Source Code Bugs
- **Discovery Validation**: Fixed `model_discovery_subcontract.py` to only validate channels when `enabled=True`
- **Port Parsing**: Enhanced `model_docker_compose_manifest.py` to handle all Docker port formats (IP prefix, protocol suffix)
- **Import Ordering**: Fixed isort configuration alignment between local and CI environments

#### Documentation Fixes
- **Missing Imports**: Added `ModelOnexError`, `CircuitBreakerError`, `datetime`, `UUID` imports to 8+ code examples
- **Enum Naming**: Standardized to `EnumCoreErrorCode` across 4+ occurrences
- **Legacy Module Paths**: Updated manifest dependency paths from `models.model_onex_error` → `errors.model_onex_error`
- **Stray Artifacts**: Removed generator artifacts from 2 template files

### Quality & CI
- **CI Performance**: All test splits running within expected 2m30s-3m30s benchmark
- **Test Coverage**: Maintained 60%+ coverage requirement with 12,198 tests
- **Type Safety**: 100% mypy strict compliance (0 errors in 1,840 source files)
- **Code Quality**: Black, isort, and ruff all passing

## [0.2.0] - 2025-10-31

### Added

#### Discovery System Enhancements
- **TypedDict for Discovery Stats**: Introduced `TypedDictDiscoveryStats` for type-safe statistics tracking in discovery system
- **Filtered Requests Counter**: Added `filtered_requests` counter to track requests that don't match discovery criteria (separate from errors and throttling)
- **Enhanced Error Tracking**: Added `error_count` field to discovery stats for comprehensive observability

#### Node Introspection Improvements
- **ONEX Architecture Classification**: Added `node_type` field with 4-node validation (effect, compute, reducer, orchestrator) to `ModelNodeIntrospectionEvent`
- **Node Role Support**: Added optional `node_role` field for specialization within node types
- **Source Node Tracking**: Added `source_node_id` field to `ModelOnexEnvelopeV1` for node-to-node event correlation and tracking (Note: `ModelOnexEnvelopeV1` was later renamed to `ModelOnexEnvelope` in )

#### Documentation Enhancements
- **Mermaid Diagrams**: Added 5 visual diagrams for ONEX architecture flows:
  - Four-node architecture flow with side effects
  - Intent emission and execution sequence (pure FSM pattern)
  - Action validation and execution flow (lease-based orchestration)
  - Service wrapper decision flowchart
  - Event-driven communication integrated into Intent flow
- **Research Documentation**:
  - In-Memory Event Bus Research Report (746 lines)
  - Union Type Quick Reference (319 lines)
  - Union Type Remediation Plan (1045 lines)
  - Ecosystem Directory Structure documentation (396 lines)
- **Enhanced Architecture Docs**: Improved ONEX four-node architecture documentation with better examples and terminology
- **Getting Started Updates**: Enhanced Quick Start guide with production patterns (ModelServiceCompute)
- **Node Building Guides**: Improved node type tutorials with FSM and Intent/Action pattern introductions
- **Container Types Documentation**: Comprehensive 657-line guide (docs/architecture/CONTAINER_TYPES.md) clarifying ModelContainer vs ModelONEXContainer distinction
- **Architectural Decision Record**: ADR-001 documenting protocol-based DI architecture design rationale
- **Container Type Compliance Report**: Audit report validating correct container type usage across codebase

### Changed

#### Dependencies
- **omnibase_spi Upgrade**: Updated from v0.1.1 → v0.2.0 with 9 new protocols for enhanced type safety and capability expansion

#### Discovery System Improvements
- **Error Handling**: Replaced silent exception handling with structured logging (ProtocolLogger warnings) for non-fatal discovery errors
- **TypedDict Usage**: Simplified TypedDict usage by removing defensive isinstance checks (trust TypedDict type safety)
- **Stats Initialization**: Updated discovery stats initialization and reset methods to include new `error_count` field

#### Validation Improvements
- **Validation Rules**: Replaced improper `dict[str, Any] | list[dict[str, Any]] | None` Union pattern with strongly-typed `ModelValidationRules | None`
- **Field Validators**: Enhanced validation using `ModelValidationRulesConverter` for backward compatibility with dict/list/string formats

### Fixed

#### Build & CI Fixes
- **Import Path**: Corrected import path for `EnumCoreErrorCode` from `omnibase_core.errors.error_codes` to `omnibase_core.enums.enum_core_error_code`
- **Import Ordering**: Fixed isort import ordering in `mixin_discovery_responder.py` (omnibase_core before omnibase_spi)
- **Missing Parameters**: Added missing `node_type` parameter to `create_from_node_info()` calls in introspection publisher

#### Node Introspection Fixes
- **Explicit Node Type**: Required explicit `get_node_type()` implementation in nodes, removing fallback to `__class__.__name__` which could produce invalid values
- **Validation Error Prevention**: Prevents runtime ValidationError from invalid node_type patterns through early error detection
- **Test Updates**: Updated 5 introspection publisher tests to include required `node_type` parameter

#### Configuration Fixes
- **isort/Ruff Conflict**: Resolved infinite loop where isort and ruff conflicted on import ordering for `mixin_discovery_responder.py`
- **Pre-commit Configuration**: Added proper exclusions in both ruff and isort configurations for files with intentional import ordering

#### Documentation Fixes
- **Docstring Typos**: Fixed 6 docstring typos:
  - "list[Any]en" → "listen"
  - "list[Any]: List of capabilities" → "list[str]: List of capabilities"
  - "list[Any]rather" → "list rather"
  - "list[Any]ings" → "listings"
  - "list[Any]ener" → "listener"
- **Broken Path References**: Fixed 3 broken path references to THREADING.md
- **Cross-Linking**: Added 8 navigation paths connecting beginner to advanced topics across documentation index, testing guide, protocol architecture, and event-driven patterns

### Refactored

#### Validation System
- **Backward Compatibility Removal**: Removed field_validator for `validation_rules` that provided automatic conversion from legacy dict/list/string formats
- **Strong Typing Enforcement**: `validation_rules` now strictly requires `ModelValidationRules | None` without automatic conversions
- **Cleaner Code**: Eliminated conversion logic and hidden transformations

### Tests

#### New Test Coverage
- **TypedDict Tests**: Added 262 comprehensive tests across 18 TypedDict implementations:
  - Structure validation tests for each TypedDict type
  - Field type and edge case tests (zero values, high volume, None handling)
  - Incremental update and reset scenarios
  - Error tracking and throttling scenarios
- **Test Updates**: Updated 5 introspection publisher tests for new `node_type` parameter requirement

### Chore

#### Repository Maintenance
- **Temporary File Cleanup**: Removed spurious temporary files that shouldn't be in version control:
  - ADVANCED_DOCS_VALIDATION_REPORT.md
  - performance_analysis_results.txt
- **MCP Configuration**: Cleaned up `.mcp.json` by removing all MCP server configurations and resetting to empty mcpServers object
- **Dependencies**: Updated `poetry.lock` and `pyproject.toml` for related dependencies

## [0.1.0] - 2025-10-21

### Added

#### Core Architecture
- **4-Node ONEX Pattern**: Complete implementation of EFFECT → COMPUTE → REDUCER → ORCHESTRATOR workflow architecture
- **Protocol-Driven Dependency Injection**: ModelONEXContainer with `container.get_service("ProtocolName")` pattern
- **Mixin/Subcontract System**: 38 specialized mixins for reusable behavior and cross-cutting concerns
- **Contract-Driven Development**: 17 comprehensive contracts for type-safe node development
- **Event-Driven Communication**: ModelEventEnvelope for inter-service messaging with correlation tracking
- **FSM-Based State Management**: Pure finite state machine implementation for Intent → Action workflows

#### Node Infrastructure
- `NodeEffect`: External I/O, API calls, side effects with transaction support
- `NodeCompute`: Pure transformations and algorithms with caching
- `NodeReducer`: State aggregation and persistence with FSM-based Intent emission
- `NodeOrchestrator`: Workflow coordination with dependency tracking and Action lease management
- `NodeCoreBase`: Unified base class with Protocol mixins for all node types

#### Pre-Composed Service Classes
- `ModelServiceEffect`: Pre-wired Effect node with service mode + health + events + metrics
- `ModelServiceCompute`: Pre-wired Compute node with service mode + health + events + metrics
- `ModelServiceReducer`: Pre-wired Reducer node with service mode + health + events + metrics + FSM
- `ModelServiceOrchestrator`: Pre-wired Orchestrator node with service mode + health + events + metrics + coordination

#### Mixins & Cross-Cutting Concerns
- `MixinNodeService`: Persistent service mode for long-lived MCP servers
- `MixinHealthCheck`: Health monitoring with configurable checks and reporting
- `MixinEventBus`: Event publishing/subscription for inter-node communication
- `MixinMetrics`: Performance metrics collection and reporting
- `MixinCaching`: Result caching with TTL and invalidation strategies
- `MixinCanonicalSerialization`: Deterministic JSON serialization for hashing
- `MixinEventDrivenNode`: Event-driven processing with envelope handling
- `MixinDiscoveryResponder`: Tool discovery and capability advertisement
- Additional specialized mixins for specific use cases

#### Contracts & Validation
- **Base Contracts**: ModelContractBase with version, description, and validation rules
- **Specialized Contracts**: ModelContractEffect, ModelContractCompute, ModelContractReducer, ModelContractOrchestrator
- **Subcontracts**: 6 specialized subcontract types (FSM, EventType, Aggregation, StateManagement, Routing, Caching)
- **Validation Framework**: Comprehensive runtime validation with Pydantic models
- **Migration System**: Protocol-based migration framework with rollback support

#### Models & Data Structures
- **Core Models**: ModelEventEnvelope, ModelHealthStatus, ModelSemVer, ModelMetadataToolCollection
- **Workflow Models**: ModelWorkflowStepExecution, ModelDependencyGraph with topological ordering
- **Action Models**: ModelAction (formerly Thunk) with lease semantics for single-writer guarantees
- **Discovery Models**: ModelToolDefinition, ModelToolParameter, ModelCapability
- **Security Models**: ModelPermission with granular access control
- **60+ production-ready Pydantic models** with full type safety

#### Error Handling
- **ModelOnexError Exception**: Structured error handling with Pydantic models
- **ModelOnexError**: Comprehensive error context with correlation tracking
- **Error Chaining**: Full exception context preservation with `__cause__`
- **Error Recovery**: Automatic retry logic with exponential backoff

#### Performance & Optimization
- **Compute Caching**: Automatic result caching for pure computations
- **Performance Baselines**: Baseline establishment and monitoring
- **Optimization Opportunities**: Automatic detection and recommendations
- **Metrics Collection**: Detailed performance metrics with thresholds

#### Type Safety & Validation
- **Zero Tolerance for Any**: Comprehensive type annotations throughout codebase
- **Pydantic Model Validation**: Runtime validation for all data structures
- **Protocol-Based Design**: Type-safe dependency injection via Protocols
- **MyPy Strict Mode**: Full static type checking compliance (in progress)

#### Developer Experience
- **Comprehensive Validation Scripts**: 42 validators across architecture, naming, patterns, and compliance
- **Pre-commit Hooks**: 27 custom ONEX validation hooks for code quality enforcement
- **Pattern Validation**: Automatic detection of anti-patterns and violations
- **Naming Conventions**: Enforced ONEX naming standards (SUFFIX-based)
- **Professional README**: Complete with badges for License (MIT), Python 3.12+, Black, MyPy, Pre-commit, and Framework status
- **Documentation**: Comprehensive inline documentation and docstrings

#### Testing Infrastructure
- **135+ Unit Tests**: Comprehensive test coverage across all components
- **Integration Tests**: Multi-node workflow testing
- **Performance Tests**: Baseline and optimization testing
- **Edge Case Coverage**: Extensive edge case and error scenario testing

#### Documentation
- **78+ Documentation Files**: Comprehensive documentation covering all aspects of the framework
- **Node-Building Guide Series**: Complete tutorials for building EFFECT, COMPUTE, REDUCER, and ORCHESTRATOR nodes
- **Mixin Development Guides**: Detailed guides for creating and composing mixins
- **Architecture Documentation**: In-depth architectural principles and design patterns
- **API Reference**: Complete API documentation with examples and usage patterns
- **Migration Guides**: Step-by-step migration instructions for breaking changes
- **CONTRIBUTING.md**: Comprehensive contribution guidelines following ONEX standards
- **README.md**: Professional project overview with architecture principles and quick start

#### Legal & Licensing
- **MIT LICENSE**: Open-source license granting broad permissions for use, modification, and distribution
- **Copyright Notices**: Proper attribution and copyright headers throughout codebase

### Changed

#### Breaking Changes - Thunk → Action Refactoring
- **Renamed**: `ModelThunk` → `ModelAction` for clearer intent semantics
- **Renamed**: `EnumThunkType` → `EnumActionType` for consistency
- **Field Renaming**:
  - `thunk_id` → `action_id`
  - `thunk_type` → `action_type`
  - `operation_data` → `payload`
- **Lease Management**: Added `lease_id` and `epoch` fields for single-writer semantics
- **Migration Path**: All test files and internal references updated
- **Backward Compatibility**: Field name `thunks` retained in ModelWorkflowStepExecution for compatibility

#### Architecture Improvements
- **NodeCoreBase Refactoring**: Migrated to Protocol-based mixin composition
- **FSM Implementation**: Pure FSM in Reducer with Intent emission (no backward compatibility methods)
- **Service Classes**: Eliminated boilerplate with pre-composed service wrappers
- **Method Resolution Order**: Optimized MRO for proper mixin composition

#### Code Quality Improvements
- **164 Ruff Auto-Fixes**: Removed unused imports, fixed formatting, simplified expressions
- **Import Organization**: Consistent isort configuration across codebase
- **Type Annotations**: Enhanced type coverage (ongoing)
- **Error Messages**: Improved error context and debugging information

#### Repository Management
- **Fresh Git History**: Clean git history established after migration from development backup
- **Conventional Commits**: Standardized commit message format for clarity
- **Branch Strategy**: Established main branch as primary development branch

### Deprecated
- **Backward Compatibility Methods in Reducer**: Removed all compatibility methods for previous state management
- **Manual YAML Generation**: Deprecated in favor of Pydantic model exports
- **String-Based Versions**: Enforced ModelSemVer usage throughout

### Removed
- **Legacy Thunk Terminology**: Removed from all public APIs (replaced with Action)
- **Redundant Base Classes**: Consolidated into pre-composed service classes
- **Dead Code**: Removed unused utilities and archived patterns
- **Deprecated Imports**: Cleaned up old import paths

### Fixed
- **Test Collection Errors**: Fixed 3 test files with EnumThunkType → EnumActionType imports
- **Import Errors**: Resolved circular import issues with proper dependency structure
- **Type Errors**: Fixed multiple type annotation issues (ongoing - 267 remaining)
- **Ruff Violations**: Reduced from 1037 to 873 violations
- **Pre-commit Hooks**: All 27 custom hooks passing

### Security
- **Protocol-Based DI**: Prevents direct class coupling and improves testability
- **Type Safety**: Strong typing reduces runtime errors and vulnerabilities
- **Validation**: Runtime validation of all inputs via Pydantic models
- **Error Context**: Comprehensive error tracking without exposing sensitive data

## Known Limitations (v0.1.0)

### Type Safety (In Progress)
- **MyPy Errors**: 267 remaining type errors requiring fixes
  - NodeCoreBase missing mixin attribute definitions (requires Protocol refinement)
  - ModelSemVer import issues in metadata collections
  - Type annotation gaps in utility functions
- **Target**: 0 mypy errors before v0.2.0

### Code Quality (In Progress)
- **Ruff Violations**: 873 remaining (down from 1037)
  - UP035: Deprecated typing imports (366 violations) - migrate to modern syntax
  - F403: Undefined star imports (80 violations) - explicit imports needed
  - PTH: Path operations (use pathlib.Path)
  - Other minor violations
- **Target**: <100 violations before v0.2.0

### Documentation
- **API Documentation**: Docstrings present but API docs generation pending
- **Architecture Diagrams**: Workflow diagrams and architecture visualizations pending
- **Migration Guides**: Detailed migration documentation for breaking changes pending
- **Examples**: More real-world usage examples needed

### Test Coverage
- **Current Coverage**: >60% overall coverage
- **Target**: >80% coverage before v0.2.0
- **Integration Tests**: Additional multi-service integration tests needed
- **Performance Tests**: Baseline and regression testing framework in development

### Configuration Management
- **PEP 621 Migration**: pyproject.toml still using legacy Poetry format
- **Deprecation Warnings**: 8 Poetry warnings for non-PEP 621 fields
- **Target**: Full PEP 621 compliance before v0.2.0

## Migration Guide

### From Pre-0.1.0 (Thunk → Action)

#### Import Changes
```python
# OLD
from omnibase_core.models.orchestrator.model_action import ModelThunk
from omnibase_core.enums.enum_workflow_execution import EnumThunkType

# NEW
from omnibase_core.models.orchestrator.model_action import ModelAction
from omnibase_core.enums.enum_workflow_execution import EnumActionType
```

#### Field Name Changes
```python
# OLD
thunk = ModelThunk(
    thunk_id=uuid4(),
    thunk_type=EnumThunkType.COMPUTE,
    operation_data={"key": "value"}
)

# NEW
action = ModelAction(
    action_id=uuid4(),
    action_type=EnumActionType.COMPUTE,
    payload={"key": "value"},
    lease_id=uuid4(),  # Required
    epoch=0  # Required
)
```

#### Workflow Step References
```python
# Field name 'thunks' retained for compatibility
step = ModelWorkflowStepExecution(
    step_name="my_step",
    execution_mode=EnumExecutionMode.SEQUENTIAL,
    thunks=[action]  # Still uses 'thunks' field name
)
```

### Reducer FSM Migration

#### Old Pattern (Removed)
```python
# REMOVED - No longer supported
await self.update_state(new_state)
await self.persist_state()
```

#### New Pattern (Pure FSM)
```python
# NEW - Emit Intent, Orchestrator converts to Action
intent = ModelIntent(
    intent_type=EnumIntentType.UPDATE_STATE,
    target_state=EnumMyState.PROCESSING,
    payload={"data": value}
)
await self.emit_intent(intent)
```

## Contributing

This project follows ONEX architectural patterns and standards. See CONTRIBUTING.md for guidelines.

### Code Quality Standards
- All code must pass pre-commit hooks (27 custom ONEX validators)
- Zero tolerance for `Any` types (strict type annotations required)
- Comprehensive test coverage (target: >80%)
- Pydantic models for all data structures
- Protocol-based dependency injection

### ONEX Naming Conventions
- **Classes**: `Node<Name><Type>` (e.g., `NodeDatabaseWriterEffect`)
- **Files**: `node_*_<type>.py` (e.g., `node_database_writer_effect.py`)
- **Methods**:
  - Effect: `execute_effect(contract: ModelContractEffect)`
  - Compute: `execute_compute(contract: ModelContractCompute)`
  - Reducer: `execute_reduction(contract: ModelContractReducer)`
  - Orchestrator: `execute_orchestration(contract: ModelContractOrchestrator)`

## Acknowledgments

Built with the ONEX framework principles:
- **Zero Boilerplate**: Eliminate repetitive code through base classes
- **Protocol-Driven**: Type-safe dependency injection via Protocols
- **Event-Driven**: Inter-service communication via ModelEventEnvelope
- **4-Node Pattern**: EFFECT → COMPUTE → REDUCER → ORCHESTRATOR workflow

## License

MIT License - See LICENSE file for details

---

**Note**: This is the initial public release (v0.1.0). While production-ready for many use cases, some rough edges remain (see Known Limitations). Contributions welcome!
