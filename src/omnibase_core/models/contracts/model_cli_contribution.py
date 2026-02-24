# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""
CLI Contribution Contract Model — cli.contribution.v1.

This is the foundational contract by which a node advertises CLI commands
to the ONEX registry-driven CLI system. All downstream catalog materialization,
signature verification, and argument parsing depend on this schema being
stable and published.

Contract Type:  cli.contribution.v1
Schema Version: 1.0.0

## Design Principles

- Command IDs are globally namespaced (e.g., ``com.omninode.memory.query``)
  and MUST be immutable across versions. Display names may change; IDs must not.
- The contract is fingerprinted (sha256 of canonical serialization) and signed
  with the publishing node's Ed25519 identity key.
- ``args_schema_ref`` and ``output_schema_ref`` reference registered schemas,
  never inline definitions.
- The registry rejects malformed or unsigned contracts.

## Usage

    >>> from omnibase_core.models.contracts.model_cli_contribution import (
    ...     ModelCliContribution, ModelCliCommandEntry,
    ... )
    >>> from omnibase_core.enums.enum_cli_command_risk import EnumCliCommandRisk
    >>> from omnibase_core.enums.enum_cli_command_visibility import EnumCliCommandVisibility
    >>> from omnibase_core.enums.enum_cli_invocation_type import EnumCliInvocationType

See Also:
    - docs/design/CLI_CONTRIBUTION_CONTRACT.md — Detailed spec.
    - ServiceRegistryCliContribution — Registry for contribution contracts.
"""

from __future__ import annotations

import hashlib
import json
import re
from typing import ClassVar

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from omnibase_core.enums.enum_cli_command_risk import EnumCliCommandRisk
from omnibase_core.enums.enum_cli_command_visibility import EnumCliCommandVisibility
from omnibase_core.enums.enum_cli_invocation_type import EnumCliInvocationType
from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.models.errors.model_onex_error import ModelOnexError
from omnibase_core.models.primitives.model_semver import ModelSemVer

# Globally namespaced command ID pattern: at least two dot-separated segments,
# each segment composed of lowercase letters, digits, and hyphens.
# Examples: "com.omninode.memory.query", "io.onex.cli.run"
_COMMAND_ID_PATTERN = re.compile(r"^[a-z][a-z0-9-]*(\.[a-z][a-z0-9-]*){1,}$")

# Contract type discriminator — immutable across versions.
CLI_CONTRIBUTION_CONTRACT_TYPE: str = "cli.contribution.v1"


class ModelCliInvocation(BaseModel):
    """Invocation specification for a CLI command.

    Describes how the CLI runtime dispatches the command when it is executed.

    Attributes:
        invocation_type: Dispatch mechanism (kafka_event, direct_call, etc.).
        topic: Kafka topic for KAFKA_EVENT invocations. Required when
            invocation_type is KAFKA_EVENT.
        endpoint: HTTP endpoint for HTTP_ENDPOINT invocations.
        callable_ref: Fully qualified Python callable for DIRECT_CALL.
        subprocess_cmd: Shell command string for SUBPROCESS.
    """

    invocation_type: EnumCliInvocationType = Field(
        ...,
        description="Dispatch mechanism for this command.",
    )
    topic: str | None = Field(
        default=None,
        description="Kafka topic for KAFKA_EVENT dispatch.",
    )
    endpoint: str | None = Field(
        default=None,
        description="HTTP endpoint URL for HTTP_ENDPOINT dispatch.",
    )
    callable_ref: str | None = Field(
        default=None,
        description="Fully qualified Python callable ref for DIRECT_CALL.",
    )
    subprocess_cmd: str | None = Field(
        default=None,
        description="Shell command string for SUBPROCESS dispatch.",
    )

    @model_validator(mode="after")
    def validate_invocation_target(self) -> ModelCliInvocation:
        """Ensure the required target field is set for the chosen invocation type."""
        itype = self.invocation_type
        if itype == EnumCliInvocationType.KAFKA_EVENT and not self.topic:
            raise ModelOnexError(
                message="topic is required for KAFKA_EVENT invocation",
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                invocation_type=itype,
            )
        if itype == EnumCliInvocationType.HTTP_ENDPOINT and not self.endpoint:
            raise ModelOnexError(
                message="endpoint is required for HTTP_ENDPOINT invocation",
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                invocation_type=itype,
            )
        if itype == EnumCliInvocationType.DIRECT_CALL and not self.callable_ref:
            raise ModelOnexError(
                message="callable_ref is required for DIRECT_CALL invocation",
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                invocation_type=itype,
            )
        if itype == EnumCliInvocationType.SUBPROCESS and not self.subprocess_cmd:
            raise ModelOnexError(
                message="subprocess_cmd is required for SUBPROCESS invocation",
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                invocation_type=itype,
            )
        return self

    model_config = ConfigDict(
        extra="forbid",
        from_attributes=True,
        str_strip_whitespace=True,
    )


class ModelCliCommandExample(BaseModel):
    """A single usage example for a CLI command.

    Attributes:
        description: Brief human-readable description of what the example does.
        invocation: The command-line string the user would type.
        expected_output: Optional sample of expected output.
    """

    description: str = Field(
        ...,
        min_length=1,
        description="Brief description of what this example demonstrates.",
    )
    invocation: str = Field(
        ...,
        min_length=1,
        description="The command-line string (e.g., 'onex memory query --limit 10').",
    )
    expected_output: str | None = Field(
        default=None,
        description="Sample of expected output for documentation.",
    )

    model_config = ConfigDict(
        extra="forbid",
        from_attributes=True,
        str_strip_whitespace=True,
    )


class ModelCliCommandEntry(BaseModel):
    """A single CLI command advertised by a node.

    Command IDs are globally namespaced and MUST be immutable across versions.
    Display names and descriptions may change; the ``id`` field must not.

    Attributes:
        id: Globally namespaced, immutable command identifier.
            Format: ``<reverse-domain-prefix>.<command-name>``
            Example: ``com.omninode.memory.query``
        display_name: Human-readable name shown in help and catalogs.
        description: Full description of what the command does.
        group: Logical grouping for catalog organization (e.g., "memory").
        args_schema_ref: Registry reference to the command's argument schema.
            Must point to a schema registered in the ONEX schema registry.
        output_schema_ref: Registry reference to the command's output schema.
        invocation: How the runtime dispatches this command.
        permissions: List of permission strings required to execute this command.
        risk: Risk classification governing HITL and audit requirements.
        requires_hitl: Whether human confirmation is required before execution.
        visibility: Controls surfacing in help output and discovery.
        examples: Usage examples for documentation and testing.
    """

    id: str = Field(
        ...,
        min_length=5,
        description="Globally namespaced, immutable command ID (dot notation).",
    )
    display_name: str = Field(
        ...,
        min_length=1,
        description="Human-readable display name.",
    )
    description: str = Field(
        ...,
        min_length=1,
        description="Full description of the command.",
    )
    group: str = Field(
        ...,
        min_length=1,
        description="Logical grouping for catalog organization.",
    )
    args_schema_ref: str = Field(
        ...,
        min_length=1,
        description="Registry reference to argument schema (not inline).",
    )
    output_schema_ref: str = Field(
        ...,
        min_length=1,
        description="Registry reference to output schema (not inline).",
    )
    invocation: ModelCliInvocation = Field(
        ...,
        description="Dispatch specification for this command.",
    )
    permissions: list[str] = Field(
        default_factory=list,
        description="Permission strings required to execute this command.",
    )
    risk: EnumCliCommandRisk = Field(
        default=EnumCliCommandRisk.LOW,
        description="Risk classification for HITL and audit.",
    )
    requires_hitl: bool = Field(
        default=False,
        description="Whether human confirmation is required before execution.",
    )
    visibility: EnumCliCommandVisibility = Field(
        default=EnumCliCommandVisibility.PUBLIC,
        description="Controls surfacing in help and discovery.",
    )
    examples: list[ModelCliCommandExample] = Field(
        default_factory=list,
        description="Usage examples for documentation.",
    )

    @field_validator("id", mode="after")
    @classmethod
    def validate_command_id_namespace(cls, v: str) -> str:
        """Validate that command ID is globally namespaced (dot notation).

        At least two dot-separated segments are required, each composed of
        lowercase letters, digits, and hyphens. Collisions at the registry
        level are a hard failure — IDs must be unique across all publishers.

        Args:
            v: Command ID string.

        Returns:
            Validated command ID.

        Raises:
            ModelOnexError: If the ID does not match the required format.
        """
        if not _COMMAND_ID_PATTERN.match(v):
            raise ModelOnexError(
                message=(
                    f"Command ID '{v}' is not globally namespaced. "
                    "Required format: '<segment>.<segment>[.<segment>...]' "
                    "where each segment is lowercase letters, digits, and hyphens. "
                    "Example: 'com.omninode.memory.query'"
                ),
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                command_id=v,
                expected_format="<reverse-domain>.<command-name>",
                example="com.omninode.memory.query",
            )
        return v

    @model_validator(mode="after")
    def validate_hitl_consistency(self) -> ModelCliCommandEntry:
        """Ensure requires_hitl is True when risk is CRITICAL."""
        if self.risk == EnumCliCommandRisk.CRITICAL and not self.requires_hitl:
            raise ModelOnexError(
                message=(
                    f"Command '{self.id}' has risk=CRITICAL but requires_hitl=False. "
                    "CRITICAL commands must require HITL."
                ),
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                command_id=self.id,
                risk=self.risk,
            )
        return self

    model_config = ConfigDict(
        extra="forbid",
        from_attributes=True,
        str_strip_whitespace=True,
    )


class ModelCliContribution(BaseModel):
    """CLI Contribution Contract — cli.contribution.v1.

    The formal mechanism by which a node advertises CLI commands to the
    ONEX registry-driven CLI system. This is the foundational contract
    for the registry-driven CLI: every downstream catalog materialization,
    signature verification, and argument parsing depends on this schema.

    Attributes:
        contract_type: Discriminator field — always ``cli.contribution.v1``.
        version: Schema version of this contribution contract (SemVer).
        publisher: The node ID (globally unique) publishing this contract.
        fingerprint: SHA256 of canonical serialization of the commands payload.
            Computed over the canonical JSON of ``commands`` (sorted keys,
            no null values). Used for drift detection and integrity checks.
        signature: Ed25519 signature (URL-safe base64) over the fingerprint
            bytes, using the publishing node's identity key.
        signer_public_key: URL-safe base64 encoded Ed25519 public key
            used to verify the signature. Must match the node's registered key.
        commands: List of CLI commands this node advertises.

    Example:
        >>> contribution = ModelCliContribution(
        ...     version=ModelSemVer(major=1, minor=0, patch=0),
        ...     publisher="com.omninode.memory",
        ...     fingerprint="a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2",
        ...     signature="base64sig==",
        ...     signer_public_key="base64pubkey==",
        ...     commands=[...],
        ... )
    """

    # Interface version for code generation stability
    INTERFACE_VERSION: ClassVar[ModelSemVer] = ModelSemVer(major=1, minor=0, patch=0)

    # Contract type discriminator — immutable
    contract_type: str = Field(
        default=CLI_CONTRIBUTION_CONTRACT_TYPE,
        description="Contract type discriminator — always 'cli.contribution.v1'.",
    )

    version: ModelSemVer = Field(
        ...,
        description="Schema version of this contribution contract.",
    )

    publisher: str = Field(
        ...,
        min_length=1,
        description="Globally unique node ID of the publishing node.",
    )

    fingerprint: str = Field(
        ...,
        min_length=64,
        max_length=64,
        pattern=r"^[a-f0-9]{64}$",
        description=(
            "SHA256 (hex, 64 chars) of canonical JSON serialization of the commands list. "
            "Use ModelCliContribution.compute_fingerprint(commands) to generate."
        ),
    )

    signature: str = Field(
        ...,
        min_length=1,
        description="Ed25519 signature (URL-safe base64) over fingerprint bytes.",
    )

    signer_public_key: str = Field(
        ...,
        min_length=1,
        description="URL-safe base64 encoded Ed25519 public key for signature verification.",
    )

    commands: list[ModelCliCommandEntry] = Field(
        default_factory=list,
        description="CLI commands advertised by this node.",
    )

    @field_validator("contract_type", mode="after")
    @classmethod
    def validate_contract_type(cls, v: str) -> str:
        """Enforce that contract_type is the immutable discriminator value."""
        if v != CLI_CONTRIBUTION_CONTRACT_TYPE:
            raise ModelOnexError(
                message=(
                    f"contract_type must be '{CLI_CONTRIBUTION_CONTRACT_TYPE}', got '{v}'."
                ),
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                received=v,
                expected=CLI_CONTRIBUTION_CONTRACT_TYPE,
            )
        return v

    @model_validator(mode="after")
    def validate_no_duplicate_command_ids(self) -> ModelCliContribution:
        """Reject contracts with duplicate command IDs.

        Command IDs must be unique within a single contribution contract and
        globally across the registry. This validator catches intra-contract
        duplicates; the registry catches inter-contract collisions.

        Raises:
            ModelOnexError: If any command IDs appear more than once.
        """
        if not self.commands:
            return self
        ids = [cmd.id for cmd in self.commands]
        seen: set[str] = set()
        duplicates: list[str] = []
        for cmd_id in ids:
            if cmd_id in seen:
                duplicates.append(cmd_id)
            seen.add(cmd_id)
        if duplicates:
            raise ModelOnexError(
                message=f"Duplicate command IDs in contribution: {sorted(set(duplicates))}",
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                publisher=self.publisher,
                duplicate_ids=sorted(set(duplicates)),
            )
        return self

    @model_validator(mode="after")
    def validate_fingerprint_matches_commands(self) -> ModelCliContribution:
        """Validate that the stored fingerprint matches the commands payload.

        Computes the canonical fingerprint from the current commands list and
        compares it against the stored fingerprint field.

        Raises:
            ModelOnexError: If the fingerprint does not match the commands.
        """
        expected = ModelCliContribution.compute_fingerprint(self.commands)
        if self.fingerprint != expected:
            raise ModelOnexError(
                message=(
                    "Contract fingerprint mismatch. "
                    f"Stored: {self.fingerprint[:12]}..., "
                    f"Computed: {expected[:12]}..."
                ),
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                publisher=self.publisher,
                stored_fingerprint=self.fingerprint,
                computed_fingerprint=expected,
                hint="Recompute fingerprint using ModelCliContribution.compute_fingerprint(commands)",
            )
        return self

    @staticmethod
    def compute_fingerprint(commands: list[ModelCliCommandEntry]) -> str:
        """Compute the canonical SHA256 fingerprint for a commands list.

        Serializes commands to canonical JSON (sorted keys, no null values,
        no whitespace) and returns the lowercase hex SHA256 digest.

        The fingerprint is stable: the same command list always produces
        the same fingerprint regardless of insertion order in fields.

        Args:
            commands: List of ModelCliCommandEntry objects.

        Returns:
            Lowercase hex SHA256 digest (64 characters).

        Example:
            >>> fp = ModelCliContribution.compute_fingerprint([])
            >>> len(fp)
            64
        """
        # Serialize each command to a canonical dict (sorted keys)
        serialized: list[object] = []
        for cmd in commands:
            raw = cmd.model_dump(exclude_none=True)
            serialized.append(_sort_dict_recursive(raw))

        canonical_json = json.dumps(
            serialized,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
        )
        return hashlib.sha256(canonical_json.encode("utf-8")).hexdigest()

    model_config = ConfigDict(
        extra="forbid",
        from_attributes=True,
        str_strip_whitespace=True,
        validate_assignment=True,
    )


def _sort_dict_recursive(obj: object) -> object:
    """Recursively sort dict keys for canonical serialization.

    Args:
        obj: Any Python object.

    Returns:
        The same object with all nested dict keys sorted.
    """
    if isinstance(obj, dict):
        return {k: _sort_dict_recursive(v) for k, v in sorted(obj.items())}
    if isinstance(obj, list):
        return [_sort_dict_recursive(item) for item in obj]
    return obj


__all__ = [
    "CLI_CONTRIBUTION_CONTRACT_TYPE",
    "ModelCliCommandEntry",
    "ModelCliCommandExample",
    "ModelCliContribution",
    "ModelCliInvocation",
]
