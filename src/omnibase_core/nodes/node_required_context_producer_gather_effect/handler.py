# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""EFFECT boundary for head sources and the base branch's manifest."""

import subprocess
from pathlib import Path

from omnibase_core.models.nodes.no_utcnow_check.model_source_file import ModelSourceFile
from omnibase_core.models.nodes.required_context_producer_check.model_required_context_producer_check_input import (
    ModelRequiredContextProducerCheckInput,
)
from omnibase_core.models.nodes.required_context_producer_check.model_required_context_producer_gather_input import (
    ModelRequiredContextProducerGatherInput,
)
from omnibase_core.validators.no_unguarded_git_subprocess import scrub_git_location_env


class NodeRequiredContextProducerGatherEffect:
    """Read only the selected repository; never inherit another Git location."""

    def handle(
        self, request: ModelRequiredContextProducerGatherInput
    ) -> ModelRequiredContextProducerCheckInput:
        """Collect head files and optionally read the base manifest with git show."""
        root = Path(request.repo_root).resolve()
        errors: list[str] = []
        head: str | None = None
        base: str | None = None
        workflows: list[ModelSourceFile] = []
        try:
            head = (root / request.manifest_path).read_text(encoding="utf-8")
        except (OSError, UnicodeError) as exc:
            errors.append(f"ERROR: {request.manifest_path}: {exc}")
        try:
            paths = sorted(
                path
                for path in (root / request.workflows_dir).iterdir()
                if path.suffix in (".yml", ".yaml") and path.is_file()
            )
            for path in paths:
                relative = path.relative_to(root).as_posix()
                try:
                    workflows.append(
                        ModelSourceFile(
                            path=relative, source=path.read_text(encoding="utf-8")
                        )
                    )
                except (OSError, UnicodeError) as exc:
                    errors.append(f"ERROR: {relative}: {exc}")
        except (OSError, ValueError) as exc:
            errors.append(f"ERROR: {request.workflows_dir}: {exc}")
        if not workflows:
            errors.append(
                f"ERROR: zero workflow files scanned under {request.workflows_dir}: "
                "a run that scans nothing is ERROR, never PASS"
            )
        if request.base is not None:
            try:
                resolved = subprocess.run(
                    [
                        "git",
                        "rev-parse",
                        "--verify",
                        "--quiet",
                        f"{request.base}^{{commit}}",
                    ],
                    cwd=root,
                    env=scrub_git_location_env(),
                    capture_output=True,
                    text=True,
                    check=False,
                )
                if resolved.returncode != 0:
                    # An explicit base that does not resolve would silently reduce the
                    # gate to a head-only check, the silence this node exists to end.
                    errors.append(
                        f"ERROR: base ref {request.base!r} does not resolve to a commit: "
                        "the removal check cannot compare against it, ERROR, never PASS"
                    )
                else:
                    result = subprocess.run(
                        ["git", "show", f"{request.base}:{request.manifest_path}"],
                        cwd=root,
                        env=scrub_git_location_env(),
                        capture_output=True,
                        text=True,
                        encoding="utf-8",
                        check=False,
                    )
                    if result.returncode == 0:
                        base = result.stdout
            except (OSError, UnicodeError) as exc:
                errors.append(
                    f"ERROR: base {request.base}:{request.manifest_path}: {exc}"
                )
        return ModelRequiredContextProducerCheckInput(
            head_manifest_text=head,
            base_manifest_text=base,
            base_ref=request.base,
            manifest_path=request.manifest_path,
            head_workflows=tuple(workflows),
            runtime_errors=tuple(errors),
            runtime_exit_code=2,
        )
