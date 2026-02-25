#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""
End-to-end integration tests for the registry-driven dynamic CLI.

Covers the full flow from contract publication through CLI command discovery
and invocation, as required by OMN-2587 epic DoD:

    node defines contract → publishes to registry → omn refresh loads catalog
    → omn <command> --help renders schema-driven help
    → omn <command> <args> dispatches to correct event topic
    → omn explain <command> shows contract details  [pytest.mark.omn_explain]
    → omn lock generates lockfile                   [pytest.mark.omn_lock]
    → omn lock --check passes against current catalog [pytest.mark.omn_lock]
    → contract mutation causes omn lock --check to fail [pytest.mark.omn_lock]

Parallel-PR features (OMN-2570 omn-lock, OMN-2576 omn-explain, OMN-2581
shell-completion) are tested with conditional markers so that the core
integration suite passes before those PRs land. Enable those tests by
running:

    pytest -m integration             # core flow only (default)
    pytest -m "integration or omn_lock"    # enable lock tests
    pytest -m "integration or omn_explain" # enable explain tests

No live external registry is required — all tests use in-process fixtures.
"""

from __future__ import annotations

import json
from argparse import Namespace
from pathlib import Path
from typing import Any

import pytest

from omnibase_core.crypto.crypto_ed25519_signer import generate_keypair, sign_base64
from omnibase_core.enums.enum_cli_command_risk import EnumCliCommandRisk
from omnibase_core.enums.enum_cli_command_visibility import EnumCliCommandVisibility
from omnibase_core.enums.enum_cli_invocation_type import EnumCliInvocationType
from omnibase_core.models.contracts.model_cli_command_entry import ModelCliCommandEntry
from omnibase_core.models.contracts.model_cli_contribution import ModelCliContribution
from omnibase_core.models.contracts.model_cli_invocation import ModelCliInvocation
from omnibase_core.models.primitives.model_semver import ModelSemVer
from omnibase_core.services.catalog.service_catalog_manager import (
    CatalogLoadError,
    ServiceCatalogManager,
)
from omnibase_core.services.cli.service_command_dispatcher import (
    ServiceCommandDispatcher,
)
from omnibase_core.services.cli.service_schema_argument_parser import (
    ServiceSchemaArgumentParser,
)
from omnibase_core.services.registry.service_registry_cli_contribution import (
    ServiceRegistryCliContribution,
)

# All tests in this file are integration tests.
pytestmark = pytest.mark.integration

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# Test node identity — globally-namespaced publisher ID
_TEST_PUBLISHER = "com.omninode.test.e2e"

# Test command — must satisfy the command ID pattern (>=2 dot-separated segments)
_TEST_COMMAND_ID = "com.omninode.test.e2e.run"
_TEST_COMMAND_TOPIC = "onex.cmd.test.e2e.run.v1"


# ---------------------------------------------------------------------------
# Fake Kafka producer (in-process stub — no network required)
# ---------------------------------------------------------------------------


class _FakeKafkaProducer:
    """In-process Kafka stub that records produced messages."""

    def __init__(self) -> None:
        self.produced: list[dict[str, Any]] = []
        self.flushed: bool = False

    def produce(self, topic: str, key: str, value: bytes) -> None:
        self.produced.append({"topic": topic, "key": key, "value": value})

    def flush(self, timeout: float = 5.0) -> None:
        self.flushed = True


# ---------------------------------------------------------------------------
# Test node helpers
# ---------------------------------------------------------------------------


def _make_invocation(topic: str = _TEST_COMMAND_TOPIC) -> ModelCliInvocation:
    """Build a minimal valid KAFKA_EVENT invocation."""
    return ModelCliInvocation(
        invocation_type=EnumCliInvocationType.KAFKA_EVENT,
        topic=topic,
    )


def _make_command_entry(
    cmd_id: str = _TEST_COMMAND_ID,
    topic: str = _TEST_COMMAND_TOPIC,
) -> ModelCliCommandEntry:
    """Build a minimal valid command entry for the test node."""
    return ModelCliCommandEntry(
        id=cmd_id,
        display_name="E2E Test Run",
        description="Execute an end-to-end test operation.",
        group="test",
        args_schema_ref=f"{cmd_id}.args.v1",
        output_schema_ref=f"{cmd_id}.output.v1",
        invocation=_make_invocation(topic=topic),
        risk=EnumCliCommandRisk.LOW,
        requires_hitl=False,
        visibility=EnumCliCommandVisibility.PUBLIC,
    )


def _build_contribution(
    commands: list[ModelCliCommandEntry],
    publisher: str = _TEST_PUBLISHER,
) -> ModelCliContribution:
    """Build a fully-signed cli.contribution.v1 contract."""
    keypair = generate_keypair()
    fingerprint = ModelCliContribution.compute_fingerprint(commands)
    signature = sign_base64(keypair.private_key_bytes, fingerprint.encode("utf-8"))

    return ModelCliContribution(
        version=ModelSemVer(major=1, minor=0, patch=0),
        publisher=publisher,
        fingerprint=fingerprint,
        signature=signature,
        signer_public_key=keypair.public_key_base64(),
        commands=commands,
    )


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def test_command() -> ModelCliCommandEntry:
    """A minimal valid command entry for the test node."""
    return _make_command_entry()


@pytest.fixture
def test_contribution(test_command: ModelCliCommandEntry) -> ModelCliContribution:
    """A signed cli.contribution.v1 contract for the test node."""
    return _build_contribution([test_command])


@pytest.fixture
def registry(test_contribution: ModelCliContribution) -> ServiceRegistryCliContribution:
    """An in-process registry pre-populated with the test contribution."""
    reg = ServiceRegistryCliContribution()
    reg.publish(test_contribution)
    return reg


@pytest.fixture
def catalog_with_cache(
    registry: ServiceRegistryCliContribution,
    tmp_path: Path,
) -> ServiceCatalogManager:
    """A catalog manager that has been refreshed to a temp cache file."""
    manager = ServiceCatalogManager(
        registry=registry,
        cache_path=tmp_path / "catalog.json",
        cli_version="0.21.0",
    )
    manager.refresh()
    return manager


@pytest.fixture
def fake_producer() -> _FakeKafkaProducer:
    """An in-process Kafka stub."""
    return _FakeKafkaProducer()


@pytest.fixture
def dispatcher(fake_producer: _FakeKafkaProducer) -> ServiceCommandDispatcher:
    """A dispatcher wired to the fake Kafka producer."""
    return ServiceCommandDispatcher(kafka_producer=fake_producer)


# ---------------------------------------------------------------------------
# Test: Phase 1 — contract definition and publication
# ---------------------------------------------------------------------------


class TestContractPublication:
    """A test node defines and publishes a cli.contribution.v1 contract."""

    def test_command_entry_valid(self, test_command: ModelCliCommandEntry) -> None:
        """Command entry is constructed and validates successfully."""
        assert test_command.id == _TEST_COMMAND_ID
        assert (
            test_command.invocation.invocation_type == EnumCliInvocationType.KAFKA_EVENT
        )
        assert test_command.invocation.topic == _TEST_COMMAND_TOPIC

    def test_fingerprint_is_stable(self, test_command: ModelCliCommandEntry) -> None:
        """Same command list always produces the same fingerprint."""
        fp1 = ModelCliContribution.compute_fingerprint([test_command])
        fp2 = ModelCliContribution.compute_fingerprint([test_command])
        assert fp1 == fp2
        assert len(fp1) == 64
        assert all(c in "0123456789abcdef" for c in fp1)

    def test_signed_contribution_builds(
        self, test_contribution: ModelCliContribution
    ) -> None:
        """Signed contribution constructs without error."""
        assert test_contribution.publisher == _TEST_PUBLISHER
        assert len(test_contribution.commands) == 1
        assert test_contribution.commands[0].id == _TEST_COMMAND_ID

    def test_registry_accepts_contribution(
        self, test_contribution: ModelCliContribution
    ) -> None:
        """Registry accepts a valid signed contribution."""
        reg = ServiceRegistryCliContribution()
        reg.publish(test_contribution)
        assert reg.has_command(_TEST_COMMAND_ID)
        retrieved = reg.get_command(_TEST_COMMAND_ID)
        assert retrieved is not None
        assert retrieved.id == _TEST_COMMAND_ID

    def test_registry_rejects_duplicate_command_id(
        self, test_contribution: ModelCliContribution
    ) -> None:
        """Registry raises ModelOnexError on duplicate global command ID."""
        from omnibase_core.models.errors.model_onex_error import ModelOnexError

        reg = ServiceRegistryCliContribution()
        reg.publish(test_contribution)

        # Build a second contribution from a different publisher but same command ID
        cmd2 = _make_command_entry(cmd_id=_TEST_COMMAND_ID, topic="onex.cmd.other.v1")
        contrib2 = _build_contribution([cmd2], publisher="com.omninode.test.other")

        with pytest.raises(ModelOnexError):
            reg.publish(contrib2)


# ---------------------------------------------------------------------------
# Test: Phase 2 — catalog load (omn refresh simulation)
# ---------------------------------------------------------------------------


class TestCatalogLoad:
    """omn refresh loads the contract into the local catalog."""

    def test_refresh_builds_catalog(
        self, catalog_with_cache: ServiceCatalogManager
    ) -> None:
        """refresh() builds the in-memory catalog and writes cache."""
        commands = catalog_with_cache.list_commands()
        assert any(cmd.id == _TEST_COMMAND_ID for cmd in commands)

    def test_load_from_cache_restores_catalog(
        self,
        registry: ServiceRegistryCliContribution,
        tmp_path: Path,
    ) -> None:
        """load() from cache restores the catalog without hitting registry."""
        cache_path = tmp_path / "catalog.json"
        manager = ServiceCatalogManager(
            registry=registry,
            cache_path=cache_path,
            cli_version="0.21.0",
        )
        manager.refresh()

        # Load-only manager (no registry access)
        load_only = ServiceCatalogManager(
            registry=None,
            cache_path=cache_path,
            cli_version="0.21.0",
        )
        load_only.load()

        cmd = load_only.get_command(_TEST_COMMAND_ID)
        assert cmd is not None
        assert cmd.id == _TEST_COMMAND_ID

    def test_load_raises_on_missing_cache(self, tmp_path: Path) -> None:
        """load() raises CatalogLoadError when cache file is missing."""
        manager = ServiceCatalogManager(
            registry=None,
            cache_path=tmp_path / "nonexistent.json",
        )
        with pytest.raises(CatalogLoadError, match="omn refresh"):
            manager.load()

    def test_get_command_after_refresh(
        self, catalog_with_cache: ServiceCatalogManager
    ) -> None:
        """get_command returns the correct entry after refresh."""
        entry = catalog_with_cache.get_command(_TEST_COMMAND_ID)
        assert entry is not None
        assert entry.display_name == "E2E Test Run"
        assert entry.group == "test"

    def test_diff_shows_added_command(
        self,
        registry: ServiceRegistryCliContribution,
        tmp_path: Path,
    ) -> None:
        """refresh() returns a diff showing added commands on first load."""
        manager = ServiceCatalogManager(
            registry=registry,
            cache_path=tmp_path / "catalog.json",
            cli_version="0.21.0",
        )
        diff = manager.refresh()
        # diff.added contains command ID strings
        assert _TEST_COMMAND_ID in diff.added


# ---------------------------------------------------------------------------
# Test: Phase 3 — schema-driven argument parsing (omn <command> --help)
# ---------------------------------------------------------------------------


class TestSchemaArgumentParsing:
    """omn <command> --help renders schema-driven help."""

    def test_parser_builds_from_schema(
        self, test_command: ModelCliCommandEntry
    ) -> None:
        """ServiceSchemaArgumentParser builds a parser from a simple schema."""
        schema: dict[str, Any] = {
            "type": "object",
            "properties": {
                "limit": {
                    "type": "integer",
                    "description": "Max results to return.",
                    "default": 10,
                },
                "query": {
                    "type": "string",
                    "description": "Search query string.",
                },
            },
            "required": ["query"],
        }

        parser = ServiceSchemaArgumentParser.from_schema(
            command_id=test_command.id,
            display_name=test_command.display_name,
            description=test_command.description,
            args_schema=schema,
            permissions=list(test_command.permissions),
            risk=test_command.risk.value,
        )
        assert parser is not None

        # Parse valid args
        ns = parser.parse_args(["--query", "hello", "--limit", "5"])
        assert ns.query == "hello"
        assert ns.limit == 5

    def test_parser_includes_json_flag(
        self, test_command: ModelCliCommandEntry
    ) -> None:
        """Every dynamic command parser includes --json flag."""
        schema: dict[str, Any] = {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "query"},
            },
            "required": ["query"],
        }
        parser = ServiceSchemaArgumentParser.from_schema(
            command_id=test_command.id,
            display_name=test_command.display_name,
            description=test_command.description,
            args_schema=schema,
            permissions=list(test_command.permissions),
            risk=test_command.risk.value,
        )
        ns = parser.parse_args(["--query", "x", "--json"])
        assert hasattr(ns, "json") and ns.json is True

    def test_parser_enforces_required_fields(
        self, test_command: ModelCliCommandEntry
    ) -> None:
        """Parser exits with error when required args are missing."""
        schema: dict[str, Any] = {
            "type": "object",
            "properties": {
                "required_field": {"type": "string", "description": "required"},
            },
            "required": ["required_field"],
        }
        parser = ServiceSchemaArgumentParser.from_schema(
            command_id=test_command.id,
            display_name=test_command.display_name,
            description=test_command.description,
            args_schema=schema,
            permissions=list(test_command.permissions),
            risk=test_command.risk.value,
        )
        with pytest.raises(SystemExit):
            parser.parse_args([])  # missing required_field


# ---------------------------------------------------------------------------
# Test: Phase 4 — risk gate + dispatch (omn <command> <args>)
# ---------------------------------------------------------------------------


class TestCommandDispatch:
    """omn <command> <args> dispatches to the correct event topic with validated args."""

    def test_low_risk_dispatches_immediately(
        self,
        test_command: ModelCliCommandEntry,
        dispatcher: ServiceCommandDispatcher,
        fake_producer: _FakeKafkaProducer,
    ) -> None:
        """LOW-risk command dispatches immediately without gate."""
        parsed_args = Namespace(limit=5, query="test-query")
        result = dispatcher.dispatch(test_command, parsed_args)

        assert result.success is True
        assert result.correlation_id is not None
        assert len(fake_producer.produced) == 1
        assert fake_producer.produced[0]["topic"] == _TEST_COMMAND_TOPIC

    def test_dispatched_payload_contains_args(
        self,
        test_command: ModelCliCommandEntry,
        dispatcher: ServiceCommandDispatcher,
        fake_producer: _FakeKafkaProducer,
    ) -> None:
        """Dispatched Kafka payload contains the parsed args as JSON."""
        parsed_args = Namespace(query="semantic-search", limit=42)
        result = dispatcher.dispatch(test_command, parsed_args)

        assert result.success is True
        payload_bytes = fake_producer.produced[0]["value"]
        payload: dict[str, Any] = json.loads(payload_bytes)

        # Payload must include the command reference and correlation_id.
        # The dispatcher uses "command_ref" (the command entry .id field).
        assert "command_ref" in payload
        assert payload["command_ref"] == _TEST_COMMAND_ID
        assert "correlation_id" in payload

    def test_medium_risk_requires_confirmation(
        self,
        dispatcher: ServiceCommandDispatcher,
    ) -> None:
        """MEDIUM-risk command blocks dispatch and requests confirmation."""
        from omnibase_core.models.cli.model_risk_gate_result import (
            GateResultPromptConfirmation,
        )

        medium_risk_cmd = _make_command_entry()
        # Build a MEDIUM risk command
        medium_risk_cmd = ModelCliCommandEntry(
            id="com.omninode.test.e2e.medium",
            display_name="Medium Risk Test",
            description="A medium-risk test command.",
            group="test",
            args_schema_ref="com.omninode.test.e2e.medium.args.v1",
            output_schema_ref="com.omninode.test.e2e.medium.output.v1",
            invocation=_make_invocation("onex.cmd.test.medium.v1"),
            risk=EnumCliCommandRisk.MEDIUM,
            requires_hitl=False,
            visibility=EnumCliCommandVisibility.PUBLIC,
        )

        parsed_args = Namespace()
        result = dispatcher.dispatch(medium_risk_cmd, parsed_args)

        assert result.success is False
        assert isinstance(result.gate_result, GateResultPromptConfirmation)

    def test_correlation_id_is_valid_uuid(
        self,
        test_command: ModelCliCommandEntry,
        dispatcher: ServiceCommandDispatcher,
    ) -> None:
        """Dispatched correlation ID is a valid UUID4."""
        import uuid

        parsed_args = Namespace()
        result = dispatcher.dispatch(test_command, parsed_args)

        assert result.success is True
        assert result.correlation_id is not None
        parsed_uuid = uuid.UUID(result.correlation_id)
        assert parsed_uuid.version == 4


# ---------------------------------------------------------------------------
# Test: Phase 5 — omn lock (gated on omn_lock marker, OMN-2570)
# ---------------------------------------------------------------------------


class TestLockfile:
    """omn lock generates a lockfile pinning contract fingerprints.

    These tests are gated behind the ``omn_lock`` marker. They pass when
    the OMN-2570 omn-lock service is available. Until that PR lands:

        pytest -m "not omn_lock"
    """

    @pytest.mark.omn_lock
    def test_lock_generates_lockfile(
        self,
        catalog_with_cache: ServiceCatalogManager,
        tmp_path: Path,
    ) -> None:
        """omn lock generates a lockfile pinning all command fingerprints."""
        try:
            from omnibase_core.services.cli.service_catalog_lock import (  # type: ignore[import]
                ServiceCatalogLock,
            )
        except ImportError:
            pytest.skip("ServiceCatalogLock not yet available (OMN-2570)")

        lockfile_path = tmp_path / "catalog.lock.json"
        lock_service = ServiceCatalogLock(catalog=catalog_with_cache)
        lock_service.generate(lockfile_path)

        assert lockfile_path.exists()
        lock_data = json.loads(lockfile_path.read_text())
        assert _TEST_COMMAND_ID in lock_data.get("commands", {})

    @pytest.mark.omn_lock
    def test_lock_check_passes_against_current_catalog(
        self,
        catalog_with_cache: ServiceCatalogManager,
        test_contribution: ModelCliContribution,
        tmp_path: Path,
    ) -> None:
        """omn lock --check passes when catalog matches lockfile."""
        try:
            from omnibase_core.services.cli.service_catalog_lock import (  # type: ignore[import]
                ServiceCatalogLock,
            )
        except ImportError:
            pytest.skip("ServiceCatalogLock not yet available (OMN-2570)")

        lockfile_path = tmp_path / "catalog.lock.json"
        lock_service = ServiceCatalogLock(catalog=catalog_with_cache)
        lock_service.generate(lockfile_path)

        # Check should pass — catalog is unchanged
        lock_service.check(lockfile_path)  # should not raise

    @pytest.mark.omn_lock
    def test_lock_check_fails_on_fingerprint_mutation(
        self,
        registry: ServiceRegistryCliContribution,
        tmp_path: Path,
    ) -> None:
        """Contract mutation causes omn lock --check to fail with drift error."""
        try:
            from omnibase_core.services.cli.service_catalog_lock import (  # type: ignore[import]
                CatalogDriftError,
                ServiceCatalogLock,
            )
        except ImportError:
            pytest.skip("ServiceCatalogLock not yet available (OMN-2570)")

        # Refresh with the original contribution
        cache_path = tmp_path / "catalog.json"
        manager = ServiceCatalogManager(
            registry=registry,
            cache_path=cache_path,
            cli_version="0.21.0",
        )
        manager.refresh()

        lockfile_path = tmp_path / "catalog.lock.json"
        lock_service = ServiceCatalogLock(catalog=manager)
        lock_service.generate(lockfile_path)

        # Mutate the registry: replace contribution with a different command description
        new_cmd = ModelCliCommandEntry(
            id=_TEST_COMMAND_ID,
            display_name="E2E Test Run MUTATED",
            description="Mutated description changes fingerprint.",
            group="test",
            args_schema_ref=f"{_TEST_COMMAND_ID}.args.v1",
            output_schema_ref=f"{_TEST_COMMAND_ID}.output.v1",
            invocation=_make_invocation(),
            risk=EnumCliCommandRisk.LOW,
            requires_hitl=False,
            visibility=EnumCliCommandVisibility.PUBLIC,
        )
        new_contribution = _build_contribution([new_cmd])
        registry.replace(new_contribution)
        manager.refresh()  # reload catalog with mutated contribution

        # lock --check must detect the fingerprint drift
        with pytest.raises(CatalogDriftError):
            lock_service.check(lockfile_path)


# ---------------------------------------------------------------------------
# Test: omn explain (gated on omn_explain marker, OMN-2576)
# ---------------------------------------------------------------------------


class TestExplain:
    """omn explain <command> shows contract details.

    Gated behind the ``omn_explain`` marker until OMN-2576 lands.
    """

    @pytest.mark.omn_explain
    def test_explain_returns_contract_details(
        self,
        catalog_with_cache: ServiceCatalogManager,
    ) -> None:
        """omn explain shows full contract details for a command."""
        try:
            from omnibase_core.services.cli.service_cli_explain import (  # type: ignore[import]
                ServiceCliExplain,
            )
        except ImportError:
            pytest.skip("ServiceCliExplain not yet available (OMN-2576)")

        explain_service = ServiceCliExplain(catalog=catalog_with_cache)
        details = explain_service.explain(_TEST_COMMAND_ID)

        assert details is not None
        assert details.get("id") == _TEST_COMMAND_ID
        assert "invocation" in details


# ---------------------------------------------------------------------------
# Test: Static core commands — omn version, status, registry, doctor, refresh
# ---------------------------------------------------------------------------


class TestStaticCoreCommands:
    """Static omn core commands work correctly."""

    def test_omn_version_command(self) -> None:
        """omn version prints version without error."""
        from click.testing import CliRunner

        from omnibase_core.cli.cli_omn import omn

        runner = CliRunner()
        result = runner.invoke(omn, ["version"])
        assert result.exit_code == 0
        assert "omn version" in result.output

    def test_omn_status_no_catalog(self, tmp_path: Path) -> None:
        """omn status exits 0 and prints helpful message when catalog missing."""
        from unittest.mock import patch

        from click.testing import CliRunner

        from omnibase_core.cli.cli_omn import omn

        missing_path = tmp_path / "nonexistent" / "catalog.json"
        runner = CliRunner()

        with patch(
            "omnibase_core.cli.cli_omn._DEFAULT_CATALOG_PATH",
            missing_path,
        ):
            result = runner.invoke(omn, ["status"])

        assert result.exit_code == 0
        assert "NOT FOUND" in result.output or "omn refresh" in result.output

    def test_omn_status_with_catalog(
        self,
        catalog_with_cache: ServiceCatalogManager,
        tmp_path: Path,
    ) -> None:
        """omn status shows command count when catalog exists."""
        from unittest.mock import patch

        from click.testing import CliRunner

        from omnibase_core.cli.cli_omn import omn

        cache_path = catalog_with_cache._cache_path  # type: ignore[attr-defined]
        runner = CliRunner()

        with patch(
            "omnibase_core.cli.cli_omn._DEFAULT_CATALOG_PATH",
            cache_path,
        ):
            result = runner.invoke(omn, ["status"])

        assert result.exit_code == 0
        assert "catalog:" in result.output
        assert "commands:" in result.output

    def test_omn_registry_no_catalog(self, tmp_path: Path) -> None:
        """omn registry exits 0 when no catalog is present."""
        from unittest.mock import patch

        from click.testing import CliRunner

        from omnibase_core.cli.cli_omn import omn

        missing_path = tmp_path / "missing_catalog.json"
        runner = CliRunner()

        with patch(
            "omnibase_core.cli.cli_omn._DEFAULT_CATALOG_PATH",
            missing_path,
        ):
            result = runner.invoke(omn, ["registry"])

        assert result.exit_code == 0
        assert "registry:" in result.output or "publishers:" in result.output

    def test_omn_doctor_fails_on_missing_catalog(self, tmp_path: Path) -> None:
        """omn doctor exits non-zero and prints actionable message when catalog missing."""
        from unittest.mock import patch

        from click.testing import CliRunner

        from omnibase_core.cli.cli_omn import omn

        missing_path = tmp_path / "no_catalog.json"
        runner = CliRunner()

        with patch(
            "omnibase_core.cli.cli_omn._DEFAULT_CATALOG_PATH",
            missing_path,
        ):
            result = runner.invoke(omn, ["doctor"])

        assert result.exit_code != 0
        assert "FAIL" in result.output or "omn refresh" in result.output

    def test_omn_doctor_passes_with_valid_catalog(
        self,
        catalog_with_cache: ServiceCatalogManager,
    ) -> None:
        """omn doctor exits 0 when catalog is valid."""
        from unittest.mock import patch

        from click.testing import CliRunner

        from omnibase_core.cli.cli_omn import omn

        cache_path = catalog_with_cache._cache_path  # type: ignore[attr-defined]
        runner = CliRunner()

        with patch(
            "omnibase_core.cli.cli_omn._DEFAULT_CATALOG_PATH",
            cache_path,
        ):
            result = runner.invoke(omn, ["doctor"])

        assert result.exit_code == 0
        assert "OK" in result.output

    def test_omn_help_available(self) -> None:
        """omn --help exits 0."""
        from click.testing import CliRunner

        from omnibase_core.cli.cli_omn import omn

        runner = CliRunner()
        result = runner.invoke(omn, ["--help"])
        assert result.exit_code == 0


# ---------------------------------------------------------------------------
# Test: Full end-to-end flow (contract → catalog → parse → gate → dispatch)
# ---------------------------------------------------------------------------


class TestFullEndToEnd:
    """Complete E2E flow: publish → refresh → parse → gate → dispatch."""

    def test_full_flow_publish_to_dispatch(
        self,
        fake_producer: _FakeKafkaProducer,
        tmp_path: Path,
    ) -> None:
        """Full pipeline from contract publication through Kafka dispatch."""
        # Step 1: Test node defines command
        command = _make_command_entry()

        # Step 2: Test node signs and publishes contract
        contribution = _build_contribution([command])

        # Step 3: Registry accepts contract
        registry = ServiceRegistryCliContribution()
        registry.publish(contribution)

        # Step 4: Catalog materializes from registry (omn refresh)
        cache_path = tmp_path / "catalog.json"
        catalog = ServiceCatalogManager(
            registry=registry,
            cache_path=cache_path,
            cli_version="0.21.0",
        )
        diff = catalog.refresh()
        # diff.added contains command ID strings
        assert _TEST_COMMAND_ID in diff.added

        # Step 5: CLI discovers command from catalog
        entry = catalog.get_command(_TEST_COMMAND_ID)
        assert entry is not None

        # Step 6: Build schema-driven parser (simulates --help and arg parse)
        schema: dict[str, Any] = {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Search query."},
                "limit": {
                    "type": "integer",
                    "description": "Max results.",
                    "default": 10,
                },
            },
            "required": ["query"],
        }
        parser = ServiceSchemaArgumentParser.from_schema(
            command_id=entry.id,
            display_name=entry.display_name,
            description=entry.description,
            args_schema=schema,
            permissions=list(entry.permissions),
            risk=entry.risk.value,
        )
        parsed_args = parser.parse_args(["--query", "integration-test", "--limit", "3"])
        assert parsed_args.query == "integration-test"
        assert parsed_args.limit == 3

        # Step 7: Risk gate evaluates (LOW risk → proceed immediately)
        dispatcher = ServiceCommandDispatcher(kafka_producer=fake_producer)
        result = dispatcher.dispatch(entry, parsed_args, args_schema=schema)

        # Step 8: Command dispatched to correct Kafka topic
        assert result.success is True
        assert len(fake_producer.produced) == 1
        assert fake_producer.produced[0]["topic"] == _TEST_COMMAND_TOPIC

        # Step 9: Payload contains expected fields.
        # The dispatcher serializes the command reference as "command_ref".
        payload: dict[str, Any] = json.loads(fake_producer.produced[0]["value"])
        assert payload["command_ref"] == _TEST_COMMAND_ID
        assert "correlation_id" in payload
        assert result.correlation_id is not None

    def test_catalog_persists_across_load(
        self,
        fake_producer: _FakeKafkaProducer,
        tmp_path: Path,
    ) -> None:
        """Catalog persists to disk and reloads without registry access."""
        command = _make_command_entry()
        contribution = _build_contribution([command])

        registry = ServiceRegistryCliContribution()
        registry.publish(contribution)

        cache_path = tmp_path / "catalog.json"
        catalog = ServiceCatalogManager(
            registry=registry,
            cache_path=cache_path,
            cli_version="0.21.0",
        )
        catalog.refresh()

        # Simulate restart: new catalog manager, no registry
        reloaded = ServiceCatalogManager(
            registry=None,
            cache_path=cache_path,
            cli_version="0.21.0",
        )
        reloaded.load()

        entry = reloaded.get_command(_TEST_COMMAND_ID)
        assert entry is not None

        # Dispatch from reloaded catalog
        dispatcher = ServiceCommandDispatcher(kafka_producer=fake_producer)
        result = dispatcher.dispatch(entry, Namespace())
        assert result.success is True
