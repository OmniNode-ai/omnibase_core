# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""HandlerDirectModelCallCheckEffect: the I/O half of the direct-model-call gate.

OMN-20295. Owns every read the pure COMPUTE handler must not do: listing and
reading the repository's tracked files (``git ls-files``), reading the policy
packaged with ``node_direct_model_call_check_compute``, the committed baseline
and, with a base ref, the baseline and hook configuration as they stood at that
ref, and today's date. It returns them as one
``ModelDirectModelCallCheckInput``; the verdict is the COMPUTE node's.

The scan is always the whole repository, because a new call site can be a new
caller of an old one: the call graph needs every file.
"""

from __future__ import annotations

import subprocess
from datetime import UTC, datetime
from importlib import resources
from pathlib import Path
from typing import Final

from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.errors.model_onex_error import ModelOnexError
from omnibase_core.models.nodes.direct_model_call_check.model_direct_model_call_baseline import (
    ModelDirectModelCallBaseline,
)
from omnibase_core.models.nodes.direct_model_call_check.model_direct_model_call_baseline_entry import (
    ModelDirectModelCallBaselineEntry,
)
from omnibase_core.models.nodes.direct_model_call_check.model_direct_model_call_check_input import (
    ModelDirectModelCallCheckInput,
)
from omnibase_core.models.nodes.direct_model_call_check.model_direct_model_call_check_request import (
    ModelDirectModelCallCheckRequest,
)
from omnibase_core.models.nodes.direct_model_call_check.model_direct_model_call_policy import (
    ModelDirectModelCallPolicy,
)
from omnibase_core.models.nodes.direct_model_call_check.model_direct_model_call_source_file import (
    ModelDirectModelCallSourceFile,
)
from omnibase_core.utils.util_safe_yaml_loader import load_yaml_content_as_model

__all__ = ["HOOK_ID", "HandlerDirectModelCallCheckEffect"]

HOOK_ID: Final[str] = "check-direct-model-call"
_POLICY_PACKAGE: Final[str] = "omnibase_core.nodes.node_direct_model_call_check_compute"
_POLICY_RESOURCE: Final[str] = "policy.yaml"
_SCANNED_SUFFIXES: Final[tuple[str, ...]] = (".py", ".pyi", ".sh", ".bash")
_SHEBANG_LIMIT: Final[int] = 1_000_000
_HOOK_CONFIGS: Final[tuple[str, ...]] = (
    ".pre-commit-config.yaml",
    ".github/workflows/direct-model-call.yml",
)


def _unreadable(message: str) -> ModelOnexError:
    return ModelOnexError(
        message=message, error_code=EnumCoreErrorCode.VALIDATION_ERROR
    )


class HandlerDirectModelCallCheckEffect:
    """EFFECT handler: a repository on disk in, the COMPUTE node's input out."""

    @property
    def handler_id(self) -> str:
        return "handler_direct_model_call_check_effect"

    def handle(
        self, request: ModelDirectModelCallCheckRequest
    ) -> ModelDirectModelCallCheckInput:
        """Definition-B entry point. Raises ModelOnexError on an unreadable input:
        the gate fails closed."""
        root = Path(request.repo_root)
        baseline: tuple[ModelDirectModelCallBaselineEntry, ...] = ()
        if request.baseline_path is not None:
            baseline_file = root / request.baseline_path
            if baseline_file.is_file():
                baseline = self._parse_baseline(
                    baseline_file.read_text("utf-8"), request.baseline_path
                )
        base_baseline: tuple[ModelDirectModelCallBaselineEntry, ...] | None = None
        base_wires_gate = False
        if request.base_ref is not None:
            if request.baseline_path is None:
                raise _unreadable("--base needs --baseline <file>")
            base_raw = self._show_at_ref(root, request.base_ref, request.baseline_path)
            if base_raw is None:
                base_wires_gate = self._gate_wired_at(root, request.base_ref)
            else:
                base_baseline = self._parse_baseline(
                    base_raw, f"{request.base_ref}:{request.baseline_path}"
                )
        return ModelDirectModelCallCheckInput(
            policy=self.load_policy(),
            repo=request.repo,
            files=tuple(self._load_sources(root, self._tracked_files(root))),
            today=datetime.now(tz=UTC).date(),
            baseline_path=request.baseline_path,
            baseline=baseline,
            base_ref=request.base_ref,
            base_baseline=base_baseline,
            base_wires_gate=base_wires_gate,
        )

    @staticmethod
    def load_policy() -> ModelDirectModelCallPolicy:
        """Read the policy packaged with the COMPUTE node."""
        raw = (
            resources.files(_POLICY_PACKAGE)
            .joinpath(_POLICY_RESOURCE)
            .read_text("utf-8")
        )
        try:
            return load_yaml_content_as_model(raw, ModelDirectModelCallPolicy)
        except ModelOnexError as exc:
            raise _unreadable(f"policy.yaml is invalid: {exc}") from exc

    @staticmethod
    def _git(root: Path, *args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            ["git", *args], cwd=root, capture_output=True, text=True, check=False
        )

    def _tracked_files(self, root: Path) -> list[str]:
        result = self._git(root, "ls-files", "-z")
        if result.returncode != 0:
            raise _unreadable(f"git ls-files failed: {result.stderr.strip()}")
        return sorted(p for p in result.stdout.split("\0") if p)

    @staticmethod
    def _load_sources(
        root: Path, paths: list[str]
    ) -> list[ModelDirectModelCallSourceFile]:
        sources: list[ModelDirectModelCallSourceFile] = []
        for rel in paths:
            path = root / rel
            if not path.is_file() or path.is_symlink():
                continue
            if not rel.endswith(_SCANNED_SUFFIXES):
                if "." in path.name or path.stat().st_size > _SHEBANG_LIMIT:
                    continue
                with path.open("rb") as handle:
                    if handle.read(2) != b"#!":
                        continue
            try:
                text = path.read_text(encoding="utf-8", errors="replace")
            except OSError as exc:
                raise _unreadable(f"{rel}: unreadable: {exc}") from exc
            sources.append(ModelDirectModelCallSourceFile(path=rel, content=text))
        return sources

    @staticmethod
    def _parse_baseline(
        raw: str, source: str
    ) -> tuple[ModelDirectModelCallBaselineEntry, ...]:
        try:
            document = load_yaml_content_as_model(raw, ModelDirectModelCallBaseline)
        except ModelOnexError as exc:
            raise _unreadable(f"{source}: not a valid baseline: {exc}") from exc
        return document.entries

    def _show_at_ref(self, root: Path, ref: str, path: str) -> str | None:
        """Return ``path`` at ``ref``, or None when absent there. A bad ref is an error."""
        if (
            self._git(
                root, "rev-parse", "--verify", "--quiet", f"{ref}^{{commit}}"
            ).returncode
            != 0
        ):
            raise _unreadable(f"--base {ref!r} does not resolve to a commit")
        if self._git(root, "cat-file", "-e", f"{ref}:{path}").returncode != 0:
            return None
        show = self._git(root, "show", f"{ref}:{path}")
        if show.returncode != 0:
            raise _unreadable(f"git show {ref}:{path} failed: {show.stderr.strip()}")
        return show.stdout

    def _gate_wired_at(self, root: Path, ref: str) -> bool:
        for config in _HOOK_CONFIGS:
            text = self._show_at_ref(root, ref, config)
            if text is not None and (HOOK_ID in text or "direct_model_call" in text):
                return True
        return False
