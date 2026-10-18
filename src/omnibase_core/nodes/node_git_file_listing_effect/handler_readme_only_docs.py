# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Refuse tracked documentation outside the root README and reasoned exceptions.

The Git index is authoritative, including for policy: an unstaged policy edit
cannot grant an exception to staged documentation. All txt files are refused
unless explicitly declared machine data; requirements txt is never excepted.
"""

from __future__ import annotations

import fnmatch
import re
import subprocess
from pathlib import Path, PurePosixPath
from typing import Final

import yaml
from pydantic import ValidationError

from omnibase_core.errors.model_onex_error import ModelOnexError
from omnibase_core.models.nodes.git_file_listing.model_git_file_listing_input import (
    ModelGitFileListingInput,
)
from omnibase_core.models.nodes.readme_only_docs.model_documentation_policy import (
    ModelDocumentationPolicy,
)
from omnibase_core.models.nodes.readme_only_docs.model_readme_only_docs_input import (
    ModelReadmeOnlyDocsInput,
)
from omnibase_core.models.validation.model_validation_report import (
    ModelValidationFindingEmbed,
    ModelValidationReport,
    ModelValidationRequestRef,
)
from omnibase_core.nodes.node_git_file_listing_effect.handler import (
    NodeGitFileListingEffect,
)
from omnibase_core.utils.util_safe_yaml_loader import load_yaml_mapping_no_duplicates
from omnibase_core.validators.no_unguarded_git_subprocess import scrub_git_location_env

VALIDATOR_ID: Final = "readme-only-docs"
POLICY_PATH: Final = ".readme-only-docs.yaml"
_DOC_SUFFIXES: Final = (".md", ".mdx", ".rst", ".adoc", ".txt")
_KB_NAMES: Final = frozenset(
    {
        "knowledge_base",
        "knowledge_base_internal",
        "knowledge-base",
        "knowledge-base-internal",
    }
)


def _git(root: Path, *args: str) -> str:
    return subprocess.run(
        ["git", "-C", str(root), *args],
        check=True,
        capture_output=True,
        text=True,
        env=scrub_git_location_env(),
    ).stdout


def _knowledge_base(root: Path) -> bool:
    # An arbitrary local directory named knowledge_base is not an exemption.
    result = subprocess.run(
        ["git", "-C", str(root), "remote", "get-url", "origin"],
        check=False,
        capture_output=True,
        text=True,
        env=scrub_git_location_env(),
    )
    if result.returncode != 0:
        return False
    match = re.fullmatch(
        r"(?:https://github\.com/|git@github\.com:|ssh://git@github\.com/)OmniNode-ai/([^/]+?)(?:\.git)?/?",
        result.stdout.strip(),
        re.IGNORECASE,
    )
    return match is not None and match[1].lower() in _KB_NAMES


class HandlerReadmeOnlyDocs:
    """Use shared Git enumeration and return the canonical validator report."""

    def handle(self, request: ModelReadmeOnlyDocsInput) -> ModelValidationReport:
        try:
            root = Path(_git(request.root, "rev-parse", "--show-toplevel").strip())
            paths = (
                NodeGitFileListingEffect()
                .handle(ModelGitFileListingInput(root=root, scope="tracked"))
                .paths
            )
            if _knowledge_base(root):
                return ModelValidationReport.from_findings(
                    findings=(),
                    request=ModelValidationRequestRef(profile="strict"),
                    validators_run=(VALIDATOR_ID,),
                )
            policy = ModelDocumentationPolicy()
            if POLICY_PATH in paths:
                policy = ModelDocumentationPolicy.model_validate(
                    load_yaml_mapping_no_duplicates(
                        _git(root, "show", f":{POLICY_PATH}"), source=POLICY_PATH
                    )
                )
            findings = []
            if "README.md" not in paths:
                findings.append(
                    ModelValidationFindingEmbed(
                        validator_id=VALIDATOR_ID,
                        severity="FAIL",
                        location="README.md",
                        rule_id="root-readme-required",
                        message="The root README.md must remain tracked.",
                        remediation="Restore the root README.md.",
                    )
                )
            for path in sorted(set(paths)):
                name = PurePosixPath(path)
                if path == "README.md" or not name.name.lower().endswith(_DOC_SUFFIXES):
                    continue
                requirements = (
                    name.name.lower().startswith("requirements")
                    and name.suffix.lower() == ".txt"
                )
                if not requirements and any(
                    fnmatch.fnmatchcase(path, item.path) for item in policy.exceptions
                ):
                    continue
                findings.append(
                    ModelValidationFindingEmbed(
                        validator_id=VALIDATOR_ID,
                        severity="FAIL",
                        location=path,
                        rule_id="uv-only" if requirements else "root-readme-only",
                        message="Use uv dependency metadata; requirements txt is refused."
                        if requirements
                        else "Documentation belongs in the knowledge base; only root README.md is implicit.",
                        remediation="Remove the file or declare its machine consumer in the repository policy."
                        if not requirements
                        else "Move dependencies into pyproject.toml and uv.lock.",
                    )
                )
            return ModelValidationReport.from_findings(
                findings=tuple(findings),
                request=ModelValidationRequestRef(profile="strict"),
                validators_run=(VALIDATOR_ID,),
            )
        except (
            ModelOnexError,
            OSError,
            subprocess.SubprocessError,
            ValidationError,
            yaml.YAMLError,
            ValueError,
        ) as exc:
            return ModelValidationReport.from_runtime_errors(VALIDATOR_ID, (str(exc),))
