# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Git-only remote evidence in an isolated, complete-history bare repository."""

from __future__ import annotations

import re
import subprocess
import tempfile
import tomllib

from omnibase_core.models.validation.model_dev_tag_lineage_facts import (
    ModelDevTagLineageFacts,
)
from omnibase_core.models.validation.model_dev_tag_lineage_request import (
    ModelDevTagLineageRequest,
)
from omnibase_core.validators.no_unguarded_git_subprocess import scrub_git_location_env


class NodeDevTagLineageEffect:
    """Resolve one request; failures retain partial facts and never become passes."""

    def handle(self, request: ModelDevTagLineageRequest) -> ModelDevTagLineageFacts:
        """Contact the entry's own URL, peel to a commit and establish exact ancestry."""
        policy = request.policy
        exists: bool | None = None
        commit: str | None = None
        version: str | None = None
        on_branch: bool | None = None
        details: list[str] = []

        def facts() -> ModelDevTagLineageFacts:
            return ModelDevTagLineageFacts(
                tag_exists=exists,
                commit=commit,
                version=version,
                on_branch=on_branch,
                detail="; ".join(details) or "ok",
            )

        values = {
            "url": request.url,
            "tag": request.tag,
            "branch": request.branch,
            "project_name": policy.project_name,
        }
        values["tag_ref"] = policy.tag_ref.format(**values)
        values["branch_ref"] = policy.branch_ref.format(**values)
        values["peeled_ref"] = values["tag_ref"] + policy.peeled_suffix
        try:
            with tempfile.TemporaryDirectory(prefix="dev-tag-lineage-") as directory:

                def git(arguments: tuple[str, ...]) -> subprocess.CompletedProcess[str]:
                    env = scrub_git_location_env()
                    env["GIT_TERMINAL_PROMPT"] = "0"
                    return subprocess.run(
                        [
                            policy.git_binary,
                            *(arg.format(**values) for arg in arguments),
                        ],
                        cwd=directory,
                        env=env,
                        capture_output=True,
                        text=True,
                        check=False,
                        timeout=policy.timeout_seconds,
                    )

                initialized = git(policy.init_arguments)
                if initialized.returncode:
                    details.append(f"init: {initialized.stderr.strip()}")
                    return facts()
                remote = git(policy.remote_arguments)
                if remote.returncode:
                    details.append(f"ls-remote: {remote.stderr.strip()}")
                    return facts()
                refs: dict[str, str] = {}
                for line in remote.stdout.splitlines():
                    fields = line.split()
                    if (
                        len(fields) != 2
                        or re.fullmatch(policy.commit_pattern, fields[0]) is None
                        or fields[1] not in (values["tag_ref"], values["peeled_ref"])
                        or fields[1] in refs
                    ):
                        details.append("ls-remote: malformed or ambiguous response")
                        return facts()
                    refs[fields[1]] = fields[0]
                if values["tag_ref"] not in refs:
                    if refs:
                        details.append("ls-remote: peel without a tag ref")
                    else:
                        exists = False
                        details.append("successful remote contact returned no tag")
                    return facts()
                exists = True
                fetched = git(policy.fetch_arguments)
                if fetched.returncode:
                    details.append(f"fetch: {fetched.stderr.strip()}")
                    return facts()
                peeled = git(policy.peel_arguments)
                sha = peeled.stdout.strip()
                advertised = refs.get(values["peeled_ref"], refs[values["tag_ref"]])
                if (
                    peeled.returncode
                    or re.fullmatch(policy.commit_pattern, sha) is None
                    or sha != advertised
                ):
                    details.append(
                        f"peel: cannot establish advertised commit: {peeled.stderr.strip()}"
                    )
                    return facts()
                commit = sha
                values["commit"] = commit
                shallow = git(policy.shallow_arguments)
                if (
                    shallow.returncode
                    or shallow.stdout.strip() != policy.complete_history_value
                ):
                    details.append("ancestry: history completeness undetermined")
                else:
                    ancestry = git(policy.ancestor_arguments)
                    on_branch = {0: True, 1: False}.get(ancestry.returncode)
                    if on_branch is None:
                        details.append(f"ancestry: {ancestry.stderr.strip()}")
                document = git(policy.show_arguments)
                if document.returncode:
                    details.append(f"show: {document.stderr.strip()}")
                else:
                    parsed = tomllib.loads(document.stdout)
                    project = parsed.get("project", {})
                    value = (
                        project.get("version") if isinstance(project, dict) else None
                    )
                    if isinstance(value, str) and value:
                        version = value
                    else:
                        details.append("show: no project.version string")
        except (
            OSError,
            UnicodeError,
            subprocess.SubprocessError,
            ValueError,
            KeyError,
        ) as exc:
            details.append(str(exc))
        return facts()
