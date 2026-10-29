# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""The patterns, name lists and message templates of the dependency-direction check (OMN-21518)."""

from __future__ import annotations

import re

from pydantic import BaseModel, ConfigDict, Field, field_validator

__all__ = ["ModelDependencyDirectionRules"]


class ModelDependencyDirectionRules(BaseModel):
    """Rule data read from the rows of ``dependency_direction.validation.yaml``.

    Attributes:
        install_or_fetch_pattern: A line that installs, clones or fetches (case-insensitive).
        repository_pattern: A workflow ``repository:`` line; group 1 is the value.
        requirement_name_pattern: Captures the distribution name at the head of a requirement.
        name_separator_pattern: The separator run PEP 503 normalisation folds to ``-``.
        token_before_pattern: The lookbehind a repository token must satisfy.
        token_after_pattern: The lookahead a repository token must satisfy.
        slug_repo_pattern: The ``<org>/<repo>`` tail after the organisation; group 1 is the repository.
        script_suffixes: File suffixes classified as scripts.
        makefile_names: File names classified as scripts.
        workflow_dir_prefix: Path prefix of workflow files.
        workflow_suffixes: File suffixes of workflow files.
        dockerfile_prefixes: Lower-case file name prefixes of a Dockerfile.
        dockerfile_suffixes: Lower-case file name suffixes of a Dockerfile.
        requirements_prefixes: Lower-case file name prefixes of a requirements file.
        requirements_suffixes: Lower-case file name suffixes of a requirements file.
        python_suffix: Suffix of a Python file.
        pyproject_name: File name of the project metadata file.
        script_dirs: A Python file under one of these directories is a script.
        script_excluded_dirs: A Python file under one of these is never a script.
        fixture_dirs: Python files under one of these are test data, not read for imports.
        comment_prefix: A line starting with this (after indentation) is a comment.
        evidence_limit: Longest evidence text kept in a finding.
        remediation: The remediation text of every FAIL and baselined finding.
        violation_message: Finding text; fields path, line, repo, own_layer, target, target_layer,
            direction, channel, evidence.
        direction_same: ``direction`` of a target on the same layer.
        direction_above: ``direction`` of a target on a higher layer.
        baselined_message: Finding text of a recorded violation; fields ticket, message.
        undeclared_repo_message: Runtime error when the repository is not in the layer map; field repo.
        stale_message: Finding text of a baseline entry no file produces; fields ticket, path,
            target, channel.
        ratchet_ref_missing_message: Runtime error when the ratchet base ref is absent; field ref.
        baseline_grew_message: Runtime error for an entry the base baseline lacks; fields path,
            channel, target.
        zero_files_message: Runtime error when a full-tree run scans nothing; field root.
        baseline_header: Comment header of a written baseline file.
        ok_message: Final line on PASS or WARN; fields repo, count.
        fail_message: Final line on FAIL or ERROR; fields status, repo.
    """

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    install_or_fetch_pattern: str = Field(min_length=1)
    repository_pattern: str = Field(min_length=1)
    requirement_name_pattern: str = Field(min_length=1)
    name_separator_pattern: str = Field(min_length=1)
    token_before_pattern: str = Field(min_length=1)
    token_after_pattern: str = Field(min_length=1)
    slug_repo_pattern: str = Field(min_length=1)
    script_suffixes: tuple[str, ...]
    makefile_names: tuple[str, ...]
    workflow_dir_prefix: str = Field(min_length=1)
    workflow_suffixes: tuple[str, ...]
    dockerfile_prefixes: tuple[str, ...]
    dockerfile_suffixes: tuple[str, ...]
    requirements_prefixes: tuple[str, ...]
    requirements_suffixes: tuple[str, ...]
    python_suffix: str = Field(min_length=1)
    pyproject_name: str = Field(min_length=1)
    script_dirs: tuple[str, ...]
    script_excluded_dirs: tuple[str, ...]
    fixture_dirs: tuple[str, ...]
    comment_prefix: str = Field(min_length=1)
    evidence_limit: int = Field(ge=1)
    remediation: str = Field(min_length=1)
    violation_message: str = Field(min_length=1)
    direction_same: str = Field(min_length=1)
    direction_above: str = Field(min_length=1)
    baselined_message: str = Field(min_length=1)
    undeclared_repo_message: str = Field(min_length=1)
    stale_message: str = Field(min_length=1)
    ratchet_ref_missing_message: str = Field(min_length=1)
    baseline_grew_message: str = Field(min_length=1)
    zero_files_message: str = Field(min_length=1)
    baseline_header: str = Field(min_length=1)
    ok_message: str = Field(min_length=1)
    fail_message: str = Field(min_length=1)

    @field_validator(
        "install_or_fetch_pattern",
        "repository_pattern",
        "requirement_name_pattern",
        "name_separator_pattern",
        "token_before_pattern",
        "token_after_pattern",
        "slug_repo_pattern",
    )
    @classmethod
    def _compiles(cls, value: str) -> str:
        try:
            re.compile(value)
        except re.error as exc:
            raise ValueError(f"pattern {value!r} does not compile: {exc}") from exc
        return value
