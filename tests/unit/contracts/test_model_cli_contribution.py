#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""
Unit tests for ModelCliContribution — cli.contribution.v1 contract schema.

Covers:
    - Valid contract construction
    - Fingerprint computation stability (same content → same sha256)
    - Signed contract passes signature verification in registry
    - Registry rejects malformed or unsigned contracts
    - Duplicate command ID detection (intra-contract)
    - Invalid command ID namespace format
    - Missing required fields
    - CRITICAL risk requires requires_hitl=True
    - Invocation type target validation
    - Registry: global command ID collision across publishers
    - Registry: replace semantics
    - Registry: get_command, list_all, has_command, unpublish
"""

import hashlib
import json

import pytest
from pydantic import ValidationError

from omnibase_core.crypto.crypto_ed25519_signer import generate_keypair, sign_base64
from omnibase_core.enums.enum_cli_command_risk import EnumCliCommandRisk
from omnibase_core.enums.enum_cli_command_visibility import EnumCliCommandVisibility
from omnibase_core.enums.enum_cli_invocation_type import EnumCliInvocationType
from omnibase_core.models.contracts.model_cli_command_entry import ModelCliCommandEntry
from omnibase_core.models.contracts.model_cli_command_example import (
    ModelCliCommandExample,
)
from omnibase_core.models.contracts.model_cli_contribution import (
    CLI_CONTRIBUTION_CONTRACT_TYPE,
    ModelCliContribution,
)
from omnibase_core.models.contracts.model_cli_invocation import ModelCliInvocation
from omnibase_core.models.errors.model_onex_error import ModelOnexError
from omnibase_core.models.primitives.model_semver import ModelSemVer
from omnibase_core.services.registry.service_registry_cli_contribution import (
    ServiceRegistryCliContribution,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_invocation(
    invocation_type: EnumCliInvocationType = EnumCliInvocationType.KAFKA_EVENT,
    topic: str = "onex.cmd.test.v1",
) -> ModelCliInvocation:
    return ModelCliInvocation(
        invocation_type=invocation_type,
        topic=topic if invocation_type == EnumCliInvocationType.KAFKA_EVENT else None,
        callable_ref=(
            "omnibase_core.test.callable"
            if invocation_type == EnumCliInvocationType.DIRECT_CALL
            else None
        ),
        endpoint=(
            "http://localhost:8080/test"
            if invocation_type == EnumCliInvocationType.HTTP_ENDPOINT
            else None
        ),
        subprocess_cmd=(
            "echo test" if invocation_type == EnumCliInvocationType.SUBPROCESS else None
        ),
    )


def _make_command(
    cmd_id: str = "com.omninode.test.run",
    risk: EnumCliCommandRisk = EnumCliCommandRisk.LOW,
    requires_hitl: bool = False,
    visibility: EnumCliCommandVisibility = EnumCliCommandVisibility.PUBLIC,
) -> ModelCliCommandEntry:
    return ModelCliCommandEntry(
        id=cmd_id,
        display_name="Test Run",
        description="Execute a test operation.",
        group="test",
        args_schema_ref="com.omninode.test.run.args.v1",
        output_schema_ref="com.omninode.test.run.output.v1",
        invocation=_make_invocation(),
        risk=risk,
        requires_hitl=requires_hitl,
        visibility=visibility,
    )


def _build_contribution(
    commands: list[ModelCliCommandEntry],
    publisher: str = "com.omninode.test",
    keypair: object = None,
) -> ModelCliContribution:
    """Build a fully signed ModelCliContribution for testing."""
    if keypair is None:
        keypair = generate_keypair()

    fingerprint = ModelCliContribution.compute_fingerprint(commands)
    signature = sign_base64(keypair.private_key_bytes, fingerprint.encode("utf-8"))  # type: ignore[attr-defined]
    public_key_b64 = keypair.public_key_base64()  # type: ignore[attr-defined]

    return ModelCliContribution(
        version=ModelSemVer(major=1, minor=0, patch=0),
        publisher=publisher,
        fingerprint=fingerprint,
        signature=signature,
        signer_public_key=public_key_b64,
        commands=commands,
    )


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestEnumCliCommandRisk:
    """Tests for EnumCliCommandRisk."""

    def test_all_values_exist(self) -> None:
        assert EnumCliCommandRisk.LOW == "low"
        assert EnumCliCommandRisk.MEDIUM == "medium"
        assert EnumCliCommandRisk.HIGH == "high"
        assert EnumCliCommandRisk.CRITICAL == "critical"

    def test_requires_hitl_by_default(self) -> None:
        assert EnumCliCommandRisk.requires_hitl_by_default(EnumCliCommandRisk.CRITICAL)
        assert not EnumCliCommandRisk.requires_hitl_by_default(EnumCliCommandRisk.HIGH)
        assert not EnumCliCommandRisk.requires_hitl_by_default(EnumCliCommandRisk.LOW)

    def test_is_destructive(self) -> None:
        assert EnumCliCommandRisk.is_destructive(EnumCliCommandRisk.HIGH)
        assert EnumCliCommandRisk.is_destructive(EnumCliCommandRisk.CRITICAL)
        assert not EnumCliCommandRisk.is_destructive(EnumCliCommandRisk.LOW)
        assert not EnumCliCommandRisk.is_destructive(EnumCliCommandRisk.MEDIUM)


@pytest.mark.unit
class TestEnumCliCommandVisibility:
    """Tests for EnumCliCommandVisibility."""

    def test_all_values_exist(self) -> None:
        assert EnumCliCommandVisibility.PUBLIC == "public"
        assert EnumCliCommandVisibility.HIDDEN == "hidden"
        assert EnumCliCommandVisibility.EXPERIMENTAL == "experimental"
        assert EnumCliCommandVisibility.DEPRECATED == "deprecated"

    def test_is_surfaced(self) -> None:
        assert EnumCliCommandVisibility.is_surfaced(EnumCliCommandVisibility.PUBLIC)
        assert EnumCliCommandVisibility.is_surfaced(
            EnumCliCommandVisibility.EXPERIMENTAL
        )
        assert EnumCliCommandVisibility.is_surfaced(EnumCliCommandVisibility.DEPRECATED)
        assert not EnumCliCommandVisibility.is_surfaced(EnumCliCommandVisibility.HIDDEN)

    def test_is_production_ready(self) -> None:
        assert EnumCliCommandVisibility.is_production_ready(
            EnumCliCommandVisibility.PUBLIC
        )
        assert EnumCliCommandVisibility.is_production_ready(
            EnumCliCommandVisibility.HIDDEN
        )
        assert not EnumCliCommandVisibility.is_production_ready(
            EnumCliCommandVisibility.EXPERIMENTAL
        )
        assert not EnumCliCommandVisibility.is_production_ready(
            EnumCliCommandVisibility.DEPRECATED
        )


@pytest.mark.unit
class TestEnumCliInvocationType:
    """Tests for EnumCliInvocationType."""

    def test_all_values_exist(self) -> None:
        assert EnumCliInvocationType.KAFKA_EVENT == "kafka_event"
        assert EnumCliInvocationType.DIRECT_CALL == "direct_call"
        assert EnumCliInvocationType.HTTP_ENDPOINT == "http_endpoint"
        assert EnumCliInvocationType.SUBPROCESS == "subprocess"

    def test_is_async(self) -> None:
        assert EnumCliInvocationType.is_async(EnumCliInvocationType.KAFKA_EVENT)
        assert not EnumCliInvocationType.is_async(EnumCliInvocationType.DIRECT_CALL)

    def test_is_network_bound(self) -> None:
        assert EnumCliInvocationType.is_network_bound(EnumCliInvocationType.KAFKA_EVENT)
        assert EnumCliInvocationType.is_network_bound(
            EnumCliInvocationType.HTTP_ENDPOINT
        )
        assert not EnumCliInvocationType.is_network_bound(
            EnumCliInvocationType.DIRECT_CALL
        )
        assert not EnumCliInvocationType.is_network_bound(
            EnumCliInvocationType.SUBPROCESS
        )


# ---------------------------------------------------------------------------
# ModelCliInvocation
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestModelCliInvocation:
    """Tests for ModelCliInvocation."""

    def test_valid_kafka_invocation(self) -> None:
        inv = ModelCliInvocation(
            invocation_type=EnumCliInvocationType.KAFKA_EVENT,
            topic="onex.cmd.test.v1",
        )
        assert inv.invocation_type == EnumCliInvocationType.KAFKA_EVENT
        assert inv.topic == "onex.cmd.test.v1"

    def test_valid_direct_call_invocation(self) -> None:
        inv = ModelCliInvocation(
            invocation_type=EnumCliInvocationType.DIRECT_CALL,
            callable_ref="omnibase_core.test.MyCallable",
        )
        assert inv.callable_ref == "omnibase_core.test.MyCallable"

    def test_valid_http_endpoint_invocation(self) -> None:
        inv = ModelCliInvocation(
            invocation_type=EnumCliInvocationType.HTTP_ENDPOINT,
            endpoint="http://localhost:8080/api",
        )
        assert inv.endpoint == "http://localhost:8080/api"

    def test_valid_subprocess_invocation(self) -> None:
        inv = ModelCliInvocation(
            invocation_type=EnumCliInvocationType.SUBPROCESS,
            subprocess_cmd="echo hello",
        )
        assert inv.subprocess_cmd == "echo hello"

    def test_kafka_missing_topic_raises(self) -> None:
        with pytest.raises((ValidationError, ModelOnexError)):
            ModelCliInvocation(
                invocation_type=EnumCliInvocationType.KAFKA_EVENT,
                topic=None,
            )

    def test_direct_call_missing_callable_ref_raises(self) -> None:
        with pytest.raises((ValidationError, ModelOnexError)):
            ModelCliInvocation(
                invocation_type=EnumCliInvocationType.DIRECT_CALL,
            )

    def test_http_endpoint_missing_endpoint_raises(self) -> None:
        with pytest.raises((ValidationError, ModelOnexError)):
            ModelCliInvocation(
                invocation_type=EnumCliInvocationType.HTTP_ENDPOINT,
            )

    def test_subprocess_missing_cmd_raises(self) -> None:
        with pytest.raises((ValidationError, ModelOnexError)):
            ModelCliInvocation(
                invocation_type=EnumCliInvocationType.SUBPROCESS,
            )


# ---------------------------------------------------------------------------
# ModelCliCommandEntry
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestModelCliCommandEntry:
    """Tests for ModelCliCommandEntry."""

    def test_valid_command_entry(self) -> None:
        cmd = _make_command("com.omninode.test.run")
        assert cmd.id == "com.omninode.test.run"
        assert cmd.risk == EnumCliCommandRisk.LOW
        assert cmd.visibility == EnumCliCommandVisibility.PUBLIC

    def test_invalid_command_id_no_dots_raises(self) -> None:
        """Command IDs without dot-namespace must be rejected."""
        with pytest.raises((ValidationError, ModelOnexError)):
            _make_command("nodots")

    def test_invalid_command_id_single_segment_raises(self) -> None:
        """Single segment (no dots) must be rejected."""
        with pytest.raises((ValidationError, ModelOnexError)):
            _make_command("singleword")

    def test_invalid_command_id_uppercase_raises(self) -> None:
        """Uppercase letters in command ID must be rejected."""
        with pytest.raises((ValidationError, ModelOnexError)):
            _make_command("Com.Omninode.Test")

    def test_valid_two_segment_id(self) -> None:
        cmd = _make_command("com.test")
        assert cmd.id == "com.test"

    def test_valid_multi_segment_id(self) -> None:
        cmd = _make_command("com.omninode.memory.query.v2")
        assert cmd.id == "com.omninode.memory.query.v2"

    def test_critical_risk_without_hitl_raises(self) -> None:
        """CRITICAL risk commands must set requires_hitl=True."""
        with pytest.raises((ValidationError, ModelOnexError)):
            _make_command(
                risk=EnumCliCommandRisk.CRITICAL,
                requires_hitl=False,
            )

    def test_critical_risk_with_hitl_succeeds(self) -> None:
        cmd = _make_command(
            risk=EnumCliCommandRisk.CRITICAL,
            requires_hitl=True,
        )
        assert cmd.requires_hitl is True
        assert cmd.risk == EnumCliCommandRisk.CRITICAL

    def test_high_risk_without_hitl_is_allowed(self) -> None:
        """HIGH risk commands do not require HITL by schema."""
        cmd = _make_command(
            risk=EnumCliCommandRisk.HIGH,
            requires_hitl=False,
        )
        assert cmd.risk == EnumCliCommandRisk.HIGH

    def test_command_with_examples(self) -> None:
        example = ModelCliCommandExample(
            description="Run with limit",
            invocation="onex test run --limit 5",
            expected_output="5 results",
        )
        cmd = ModelCliCommandEntry(
            id="com.omninode.test.run",
            display_name="Test Run",
            description="Test description.",
            group="test",
            args_schema_ref="com.omninode.test.run.args.v1",
            output_schema_ref="com.omninode.test.run.output.v1",
            invocation=_make_invocation(),
            examples=[example],
        )
        assert len(cmd.examples) == 1
        assert cmd.examples[0].invocation == "onex test run --limit 5"


# ---------------------------------------------------------------------------
# ModelCliContribution — fingerprint
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestModelCliContributionFingerprint:
    """Tests for ModelCliContribution.compute_fingerprint."""

    def test_empty_commands_fingerprint_is_stable(self) -> None:
        fp1 = ModelCliContribution.compute_fingerprint([])
        fp2 = ModelCliContribution.compute_fingerprint([])
        assert fp1 == fp2
        assert len(fp1) == 64
        assert all(c in "0123456789abcdef" for c in fp1)

    def test_same_commands_produce_same_fingerprint(self) -> None:
        cmds = [_make_command("com.omninode.test.run")]
        fp1 = ModelCliContribution.compute_fingerprint(cmds)
        fp2 = ModelCliContribution.compute_fingerprint(cmds)
        assert fp1 == fp2

    def test_different_commands_produce_different_fingerprints(self) -> None:
        cmds_a = [_make_command("com.omninode.test.alpha")]
        cmds_b = [_make_command("com.omninode.test.beta")]
        assert ModelCliContribution.compute_fingerprint(
            cmds_a
        ) != ModelCliContribution.compute_fingerprint(cmds_b)

    def test_fingerprint_is_sha256_of_canonical_json(self) -> None:
        """Manual verification: fingerprint must match sha256 of canonical JSON."""
        cmds = [_make_command("com.omninode.test.run")]
        serialized = [
            _sort_dict_recursive_test(cmd.model_dump(exclude_none=True)) for cmd in cmds
        ]
        canonical = json.dumps(
            serialized, sort_keys=True, separators=(",", ":"), ensure_ascii=True
        )
        expected = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
        assert ModelCliContribution.compute_fingerprint(cmds) == expected


def _sort_dict_recursive_test(obj: object) -> object:
    """Test helper matching ModelCliContribution._sort_dict_recursive."""
    if isinstance(obj, dict):
        return {k: _sort_dict_recursive_test(v) for k, v in sorted(obj.items())}
    if isinstance(obj, list):
        return [_sort_dict_recursive_test(item) for item in obj]
    return obj


# ---------------------------------------------------------------------------
# ModelCliContribution — full model
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestModelCliContribution:
    """Tests for ModelCliContribution model validation."""

    def test_valid_contribution_empty_commands(self) -> None:
        contrib = _build_contribution(commands=[])
        assert contrib.contract_type == CLI_CONTRIBUTION_CONTRACT_TYPE
        assert contrib.publisher == "com.omninode.test"
        assert len(contrib.commands) == 0

    def test_valid_contribution_with_commands(self) -> None:
        cmds = [
            _make_command("com.omninode.test.alpha"),
            _make_command("com.omninode.test.beta"),
        ]
        contrib = _build_contribution(commands=cmds)
        assert len(contrib.commands) == 2

    def test_wrong_contract_type_raises(self) -> None:
        cmds = [_make_command()]
        fingerprint = ModelCliContribution.compute_fingerprint(cmds)
        keypair = generate_keypair()
        sig = sign_base64(keypair.private_key_bytes, fingerprint.encode("utf-8"))
        with pytest.raises((ValidationError, ModelOnexError)):
            ModelCliContribution(
                contract_type="wrong.type.v1",
                version=ModelSemVer(major=1, minor=0, patch=0),
                publisher="com.omninode.test",
                fingerprint=fingerprint,
                signature=sig,
                signer_public_key=keypair.public_key_base64(),
                commands=cmds,
            )

    def test_mismatched_fingerprint_raises(self) -> None:
        """Stored fingerprint that does not match commands must be rejected."""
        cmds = [_make_command("com.omninode.test.run")]
        keypair = generate_keypair()
        # Use a fingerprint computed from *different* commands
        wrong_fp = ModelCliContribution.compute_fingerprint([])
        sig = sign_base64(keypair.private_key_bytes, wrong_fp.encode("utf-8"))
        with pytest.raises((ValidationError, ModelOnexError)):
            ModelCliContribution(
                version=ModelSemVer(major=1, minor=0, patch=0),
                publisher="com.omninode.test",
                fingerprint=wrong_fp,
                signature=sig,
                signer_public_key=keypair.public_key_base64(),
                commands=cmds,
            )

    def test_duplicate_command_ids_within_contract_raises(self) -> None:
        """Duplicate command IDs in the same contribution must be rejected."""
        cmds = [
            _make_command("com.omninode.test.run"),
            _make_command("com.omninode.test.run"),
        ]
        keypair = generate_keypair()
        fingerprint = ModelCliContribution.compute_fingerprint(cmds)
        sig = sign_base64(keypair.private_key_bytes, fingerprint.encode("utf-8"))
        with pytest.raises((ValidationError, ModelOnexError)):
            ModelCliContribution(
                version=ModelSemVer(major=1, minor=0, patch=0),
                publisher="com.omninode.test",
                fingerprint=fingerprint,
                signature=sig,
                signer_public_key=keypair.public_key_base64(),
                commands=cmds,
            )

    def test_fingerprint_field_must_be_64_hex_chars(self) -> None:
        """Fingerprint field validates format: exactly 64 lowercase hex chars."""
        cmds: list[ModelCliCommandEntry] = []
        keypair = generate_keypair()
        correct_fp = ModelCliContribution.compute_fingerprint(cmds)
        sig = sign_base64(keypair.private_key_bytes, correct_fp.encode("utf-8"))
        # Too short fingerprint
        with pytest.raises((ValidationError, ModelOnexError)):
            ModelCliContribution(
                version=ModelSemVer(major=1, minor=0, patch=0),
                publisher="com.omninode.test",
                fingerprint="abc123",
                signature=sig,
                signer_public_key=keypair.public_key_base64(),
                commands=cmds,
            )


# ---------------------------------------------------------------------------
# ServiceRegistryCliContribution
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestServiceRegistryCliContribution:
    """Tests for ServiceRegistryCliContribution."""

    def setup_method(self) -> None:
        self.registry = ServiceRegistryCliContribution()
        self.keypair = generate_keypair()

    def _publish(
        self,
        publisher: str = "com.omninode.test",
        commands: list[ModelCliCommandEntry] | None = None,
        replace: bool = False,
    ) -> ModelCliContribution:
        if commands is None:
            commands = [_make_command("com.omninode.test.run")]
        contrib = _build_contribution(
            commands=commands, publisher=publisher, keypair=self.keypair
        )
        self.registry.publish(contrib, replace=replace, verify_signature=True)
        return contrib

    def test_publish_and_get(self) -> None:
        contrib = self._publish()
        found = self.registry.get("com.omninode.test")
        assert found is not None
        assert found.publisher == "com.omninode.test"

    def test_get_nonexistent_returns_none(self) -> None:
        assert self.registry.get("com.omninode.nonexistent") is None

    def test_publish_duplicate_raises(self) -> None:
        self._publish(publisher="com.omninode.test")
        with pytest.raises(ModelOnexError):
            self._publish(publisher="com.omninode.test", replace=False)

    def test_publish_with_replace_succeeds(self) -> None:
        self._publish(publisher="com.omninode.test")
        # Replace with a different command set
        cmds = [_make_command("com.omninode.test.run2")]
        self._publish(
            publisher="com.omninode.test",
            commands=cmds,
            replace=True,
        )
        contract = self.registry.get("com.omninode.test")
        assert contract is not None
        assert contract.commands[0].id == "com.omninode.test.run2"

    def test_get_command_found(self) -> None:
        self._publish(commands=[_make_command("com.omninode.test.run")])
        entry = self.registry.get_command("com.omninode.test.run")
        assert entry is not None
        assert entry.id == "com.omninode.test.run"

    def test_get_command_not_found(self) -> None:
        assert self.registry.get_command("com.omninode.nonexistent.cmd") is None

    def test_command_id_collision_across_publishers_raises(self) -> None:
        """Two different publishers cannot register the same command ID."""
        self._publish(
            publisher="com.omninode.alpha",
            commands=[_make_command("com.omninode.shared.cmd")],
        )
        keypair_b = generate_keypair()
        contrib_b = _build_contribution(
            commands=[_make_command("com.omninode.shared.cmd")],
            publisher="com.omninode.beta",
            keypair=keypair_b,
        )
        with pytest.raises(ModelOnexError):
            self.registry.publish(contrib_b, verify_signature=True)

    def test_unpublish_removes_contract_and_commands(self) -> None:
        self._publish(commands=[_make_command("com.omninode.test.run")])
        result = self.registry.unpublish("com.omninode.test")
        assert result is True
        assert self.registry.get("com.omninode.test") is None
        assert self.registry.get_command("com.omninode.test.run") is None

    def test_unpublish_nonexistent_returns_false(self) -> None:
        assert self.registry.unpublish("com.omninode.nonexistent") is False

    def test_list_all_returns_all_contracts(self) -> None:
        keypair_a = generate_keypair()
        keypair_b = generate_keypair()
        contrib_a = _build_contribution(
            commands=[_make_command("com.omninode.a.cmd")],
            publisher="com.omninode.a",
            keypair=keypair_a,
        )
        contrib_b = _build_contribution(
            commands=[_make_command("com.omninode.b.cmd")],
            publisher="com.omninode.b",
            keypair=keypair_b,
        )
        self.registry.publish(contrib_a, verify_signature=True)
        self.registry.publish(contrib_b, verify_signature=True)
        all_contracts = self.registry.list_all()
        assert len(all_contracts) == 2

    def test_list_all_commands_returns_flat_list(self) -> None:
        cmds = [
            _make_command("com.omninode.test.alpha"),
            _make_command("com.omninode.test.beta"),
        ]
        self._publish(commands=cmds)
        all_cmds = self.registry.list_all_commands()
        assert len(all_cmds) == 2
        ids = {c.id for c in all_cmds}
        assert "com.omninode.test.alpha" in ids
        assert "com.omninode.test.beta" in ids

    def test_has_command(self) -> None:
        self._publish(commands=[_make_command("com.omninode.test.run")])
        assert self.registry.has_command("com.omninode.test.run")
        assert not self.registry.has_command("com.omninode.nonexistent")

    def test_len(self) -> None:
        assert len(self.registry) == 0
        self._publish()
        assert len(self.registry) == 1

    def test_contains(self) -> None:
        self._publish(publisher="com.omninode.test")
        assert "com.omninode.test" in self.registry
        assert "com.omninode.other" not in self.registry

    def test_clear(self) -> None:
        self._publish()
        self.registry.clear()
        assert len(self.registry) == 0
        assert self.registry.list_all_commands() == []

    def test_invalid_signature_rejected(self) -> None:
        """Registry must reject a contract with invalid signature."""
        cmds = [_make_command("com.omninode.test.run")]
        fingerprint = ModelCliContribution.compute_fingerprint(cmds)
        keypair = generate_keypair()
        # Sign with a different key
        wrong_keypair = generate_keypair()
        wrong_sig = sign_base64(
            wrong_keypair.private_key_bytes, fingerprint.encode("utf-8")
        )
        contrib = ModelCliContribution(
            version=ModelSemVer(major=1, minor=0, patch=0),
            publisher="com.omninode.test",
            fingerprint=fingerprint,
            signature=wrong_sig,
            signer_public_key=keypair.public_key_base64(),
            commands=cmds,
        )
        with pytest.raises(ModelOnexError):
            self.registry.publish(contrib, verify_signature=True)

    def test_publish_without_signature_verification(self) -> None:
        """When verify_signature=False, invalid signature is accepted."""
        cmds = [_make_command("com.omninode.test.run")]
        fingerprint = ModelCliContribution.compute_fingerprint(cmds)
        keypair = generate_keypair()
        wrong_keypair = generate_keypair()
        wrong_sig = sign_base64(
            wrong_keypair.private_key_bytes, fingerprint.encode("utf-8")
        )
        contrib = ModelCliContribution(
            version=ModelSemVer(major=1, minor=0, patch=0),
            publisher="com.omninode.test",
            fingerprint=fingerprint,
            signature=wrong_sig,
            signer_public_key=keypair.public_key_base64(),
            commands=cmds,
        )
        # Should not raise
        self.registry.publish(contrib, verify_signature=False)
        assert self.registry.get("com.omninode.test") is not None

    def test_list_publishers(self) -> None:
        keypair_a = generate_keypair()
        keypair_b = generate_keypair()
        self.registry.publish(
            _build_contribution(
                commands=[_make_command("com.omninode.a.run")],
                publisher="com.omninode.a",
                keypair=keypair_a,
            ),
            verify_signature=True,
        )
        self.registry.publish(
            _build_contribution(
                commands=[_make_command("com.omninode.b.run")],
                publisher="com.omninode.b",
                keypair=keypair_b,
            ),
            verify_signature=True,
        )
        publishers = self.registry.list_publishers()
        assert "com.omninode.a" in publishers
        assert "com.omninode.b" in publishers

    def test_repr(self) -> None:
        self._publish()
        r = repr(self.registry)
        assert "ServiceRegistryCliContribution" in r
        assert "publishers=1" in r
