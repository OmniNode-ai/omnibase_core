# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""Typed models for the hardcoded model-configuration COMPUTE validator (OMN-19252).

The policy, the per-file scan input, the finding, the scan result and the
baseline entry of one validator. They are co-located for the same reason as the
``validation/private_ip/models.py`` triad: none of them has a consumer outside
this validator.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

__all__ = [
    "LiteralFamily",
    "LiteralPathClass",
    "ModelHardcodedModelConfigBaseline",
    "ModelHardcodedModelConfigBaselineEntry",
    "ModelHardcodedModelConfigFinding",
    "ModelHardcodedModelConfigPathClass",
    "ModelHardcodedModelConfigPolicy",
    "ModelHardcodedModelConfigScanInput",
    "ModelHardcodedModelConfigScanResult",
]

# M: model id. E: endpoint. E-LAN: a private or lab-subnet host. R: a retired lab
# value. L: an example file loaded by code.
LiteralFamily = Literal["M", "E", "E-LAN", "R", "L"]

LiteralPathClass = Literal[
    "HISTORICAL",
    "GUARD",
    "EXAMPLE",
    "VENDOR_DEFAULT",
    "LAUNCH",
    "DOC",
    "TEST",
    "SOURCE",
]


class ModelHardcodedModelConfigPathClass(BaseModel):
    """One row of the policy's ordered path-class table. The first match wins."""

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    name: LiteralPathClass = Field(description="Path class name")
    globs: tuple[str, ...] = Field(
        default=(),
        description="Repository-relative globs ('**' spans directories)",
    )
    files: tuple[str, ...] = Field(
        default=(),
        description="Exact repository-relative file paths (no glob membership)",
    )
    families: tuple[LiteralFamily, ...] = Field(
        description="Families that apply to a path in this class"
    )


class ModelHardcodedModelConfigPolicy(BaseModel):
    """The whole allowlist and every detector input. Lives in ``policy.yaml``."""

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    schema_version: int = Field(ge=1, description="Policy schema version")
    path_classes: tuple[ModelHardcodedModelConfigPathClass, ...] = Field(
        description="Ordered path classes; the last one must be SOURCE"
    )
    model_id_pattern: str = Field(
        description="Case-insensitive model-family regex (family M)"
    )
    endpoint_path_suffixes: tuple[str, ...] = Field(
        description="URL path endings that make a URL an inference endpoint (E)"
    )
    endpoint_keys: tuple[str, ...] = Field(
        description="Keys whose URL-valued literal is an endpoint (E)"
    )
    lab_subnet_pattern: str = Field(
        description="Regex for any literal on our own lab subnet (E-LAN)"
    )
    retired_values: tuple[str, ...] = Field(
        description="Exact retired lab strings (R); matched in comments too"
    )


class ModelHardcodedModelConfigScanInput(BaseModel):
    """One file's text, already loaded by the EFFECT boundary."""

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    path: str = Field(description="Repository-relative POSIX path of the file")
    content: str = Field(description="Raw file text")


class ModelHardcodedModelConfigFinding(BaseModel):
    """One family matched on one line. Several matches of one family on a line
    are one finding, because the baseline is keyed by line content."""

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    path: str = Field(description="Repository-relative path")
    line: int = Field(ge=1, description="1-based line number")
    family: LiteralFamily = Field(description="Detector family")
    path_class: LiteralPathClass = Field(description="Path class the file fell in")
    matched_text: str = Field(description="First matched text on the line")
    content_sha1: str = Field(description="sha1 of the stripped line text")


class ModelHardcodedModelConfigScanResult(BaseModel):
    """COMPUTE verdict for one scanned file."""

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    path: str = Field(description="Repository-relative path")
    path_class: LiteralPathClass = Field(description="Path class the file fell in")
    findings: tuple[ModelHardcodedModelConfigFinding, ...] = Field(
        default=(), description="Findings in line order"
    )


class ModelHardcodedModelConfigBaselineEntry(BaseModel):
    """A pre-existing finding the ratchet tolerates, keyed by content, never by
    line number, so an unrelated edit does not churn it. Repeated identical
    lines in one file appear as repeated entries (a multiset)."""

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    path: str = Field(description="Repository-relative path")
    family: LiteralFamily = Field(description="Detector family")
    content_sha1: str = Field(
        pattern=r"^[0-9a-f]{40}$", description="sha1 of the stripped line text"
    )

    def key(self) -> tuple[str, str, str]:
        return (self.path, self.family, self.content_sha1)


class ModelHardcodedModelConfigBaseline(BaseModel):
    """The committed baseline document: a multiset of tolerated findings."""

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    schema_version: int = Field(ge=1, description="Baseline schema version")
    entries: tuple[ModelHardcodedModelConfigBaselineEntry, ...] = Field(
        default=(), description="Tolerated pre-existing findings"
    )
