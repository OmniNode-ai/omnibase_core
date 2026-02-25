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
    ...     ModelCliContribution,
    ... )
    >>> from omnibase_core.models.contracts.model_cli_command_entry import (
    ...     ModelCliCommandEntry,
    ... )
    >>> from omnibase_core.enums.enum_cli_command_risk import EnumCliCommandRisk
    >>> from omnibase_core.enums.enum_cli_command_visibility import EnumCliCommandVisibility
    >>> from omnibase_core.enums.enum_cli_invocation_type import EnumCliInvocationType

See Also:
    - docs/design/CLI_CONTRIBUTION_CONTRACT.md — Detailed spec.
    - ServiceRegistryCliContribution — Registry for contribution contracts.
    - model_cli_command_entry.py — ModelCliCommandEntry
    - model_cli_command_example.py — ModelCliCommandExample
    - model_cli_invocation.py — ModelCliInvocation
"""

from __future__ import annotations

import hashlib
import json
from typing import ClassVar

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.models.contracts.model_cli_command_entry import ModelCliCommandEntry
from omnibase_core.models.errors.model_onex_error import ModelOnexError
from omnibase_core.models.primitives.model_semver import ModelSemVer

__all__ = ["CLI_CONTRIBUTION_CONTRACT_TYPE", "ModelCliContribution"]

# Contract type discriminator — immutable across versions.
CLI_CONTRIBUTION_CONTRACT_TYPE: str = "cli.contribution.v1"


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
        ...     fingerprint="a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2",  # pragma: allowlist secret
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
