# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""Typed models for the direct-model-call COMPUTE validator (OMN-20295).

The policy, the scan input, the finding and the baseline of one validator. They
are co-located for the same reason as the ``hardcoded_model_config/models.py``
set: none of them has a consumer outside this validator.
"""

from __future__ import annotations

from datetime import date
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

__all__ = [
    "LiteralDirectModelCallKind",
    "ModelDirectModelCallBaseline",
    "ModelDirectModelCallBaselineEntry",
    "ModelDirectModelCallFinding",
    "ModelDirectModelCallPolicy",
    "ModelDirectModelCallScanInput",
    "ModelDirectModelCallSourceFile",
]

# sdk_import: a model provider SDK is imported.
# cli_exec: a model CLI (crush, codex, claude -p, llama-cli, ...) is executed.
# http: an HTTP request is built to a model endpoint, a provider host or a base_url.
# call_via: a function calls a model-calling function in another file.
# exec_via: a file executes another file of the repository that calls a model.
LiteralDirectModelCallKind = Literal[
    "sdk_import", "cli_exec", "http", "call_via", "exec_via"
]


class ModelDirectModelCallPolicy(BaseModel):
    """Every detector input and the whole set of sanctioned packages.

    Lives in ``policy.yaml`` inside this package, so a consumer repository
    cannot widen it: an exception is a reviewed change to omnibase_core.
    """

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    schema_version: int = Field(ge=1, description="Policy schema version")
    sanctioned_packages: dict[str, tuple[str, ...]] = Field(
        description=(
            "Repository name -> repository-relative globs of the sanctioned "
            "delegation node packages. A repository absent here has none."
        )
    )
    model_sdk_modules: tuple[str, ...] = Field(
        description="Top-level dotted module prefixes of model provider SDKs"
    )
    model_clis: tuple[str, ...] = Field(
        description="Program basenames that are model CLIs whatever their arguments"
    )
    print_mode_clis: tuple[str, ...] = Field(
        description="Program basenames that are model CLIs only with a print flag"
    )
    print_flags: tuple[str, ...] = Field(
        description="Flags that put a print_mode_cli into one-shot model mode"
    )
    http_clis: tuple[str, ...] = Field(
        description="Program basenames that send an HTTP request (curl, wget)"
    )
    command_wrappers: tuple[str, ...] = Field(
        description="Programs that run their first non-option argument (env, timeout)"
    )
    shells: tuple[str, ...] = Field(
        description="Programs whose -c argument is a shell command line"
    )
    python_programs: tuple[str, ...] = Field(
        description="Interpreter basenames whose script argument is executed"
    )
    http_client_modules: tuple[str, ...] = Field(
        description="Modules whose import makes a .post/.request call an HTTP send"
    )
    model_api_path_pattern: str = Field(
        description="Regex over a resolved URL text: a model API path"
    )
    provider_host_pattern: str = Field(
        description="Regex over a resolved URL text: a model provider host"
    )
    base_url_identifier_pattern: str = Field(
        description="Regex over an identifier, attribute or key naming a model base URL"
    )
    generic_base_url_identifier_pattern: str = Field(
        description=(
            "Regex over a plain base-URL identifier; a URL from one is a model "
            "call only in a file that already holds a model call"
        )
    )
    model_env_key_pattern: str = Field(
        description="Regex over an environment-variable name holding a model endpoint"
    )
    payload_keys: tuple[str, ...] = Field(
        description="A request body with any of these keys is a model request"
    )
    payload_model_companions: tuple[str, ...] = Field(
        description="A body with 'model' and any of these keys is a model request"
    )
    required_ticket_by_target: dict[str, str] = Field(
        default_factory=dict,
        description="Baseline entries for this target must name this ticket",
    )


class ModelDirectModelCallSourceFile(BaseModel):
    """One tracked file's text, already loaded by the EFFECT boundary."""

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    path: str = Field(description="Repository-relative POSIX path")
    content: str = Field(description="Raw file text")


class ModelDirectModelCallScanInput(BaseModel):
    """The whole repository: the call graph needs every file at once."""

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    repo: str = Field(description="Repository name, the key into sanctioned_packages")
    files: tuple[ModelDirectModelCallSourceFile, ...] = Field(
        description="Every scanned file of the repository"
    )


class ModelDirectModelCallFinding(BaseModel):
    """One direct model call site, keyed by what it is, never by line number."""

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    path: str = Field(description="Repository-relative path")
    line: int = Field(ge=1, description="1-based line of the site")
    kind: LiteralDirectModelCallKind = Field(description="Site kind")
    symbol: str = Field(
        description="Enclosing function qualname, '<module>' or a shell function"
    )
    target: str = Field(
        description="What is called: an SDK, a CLI, 'http', or the callee path::symbol"
    )
    evidence: str = Field(description="Why the site is a model call, for the reader")

    def key(self) -> tuple[str, str, str, str]:
        return (self.path, self.kind, self.symbol, self.target)


class ModelDirectModelCallBaselineEntry(BaseModel):
    """A pre-existing site the ratchet tolerates until its cutover ticket lands.

    Repeated identical keys in one file appear as repeated entries (a multiset).
    """

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    path: str = Field(description="Repository-relative path")
    kind: LiteralDirectModelCallKind = Field(description="Site kind")
    symbol: str = Field(description="Enclosing symbol")
    target: str = Field(description="What is called")
    ticket: str = Field(
        pattern=r"^OMN-[0-9]+$", description="The ticket that removes this site"
    )
    expires: date = Field(
        description="After this date the entry no longer covers its site"
    )

    def key(self) -> tuple[str, str, str, str]:
        return (self.path, self.kind, self.symbol, self.target)


class ModelDirectModelCallBaseline(BaseModel):
    """The committed baseline document: a multiset of tolerated sites."""

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    schema_version: int = Field(ge=1, description="Baseline schema version")
    entries: tuple[ModelDirectModelCallBaselineEntry, ...] = Field(
        default=(), description="Tolerated pre-existing sites"
    )
