# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""Subprocess-based backend for git/gh CLI operations.

Implements ProtocolGitOperations by shelling out to ``git`` and ``gh`` CLI
binaries via ``asyncio.create_subprocess_exec``.

Targeting rules:
    - git ops: ``cwd=request.working_directory`` (fallback: process cwd)
    - gh ops: ``-R {request.repo}`` when set, else ``cwd`` + infer from remote

Concurrency is capped by an ``asyncio.Semaphore`` whose width defaults to 3
and is configurable via ``OMNICLAUDE_GIT_MAX_CONCURRENT``.

Stdout is truncated at 64 KB; stderr is trimmed to the last 500 bytes and
included in FAILED results only.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import re
import subprocess
from asyncio.subprocess import PIPE
from uuid import UUID

from omniclaude.nodes.node_git_effect.handlers.handler_git_admission import (
    ruling_reread_refusal,
)
from omniclaude.nodes.node_git_effect.models import (
    GitOperation,
    ModelGitRequest,
    ModelGitResult,
)
from omniclaude.nodes.node_git_effect.models.model_git_result import GitResultStatus

__all__ = ["HandlerGitSubprocess"]

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_MAX_OUTPUT_BYTES: int = 64 * 1024  # 64 KB
_STDERR_TAIL_BYTES: int = 500
_TRUNCATION_MARKER: str = "\n... [truncated at 64 KB]"

# Ticket stamp markers (OMN-2817 1g)
TICKET_STAMP_START = "<!-- ONEX_TICKET_STAMP_START -->"
TICKET_STAMP_END = "<!-- ONEX_TICKET_STAMP_END -->"

TICKET_STAMP_TEMPLATE = """{start}
**Ticket**: [{ticket_id}](https://linear.app/omninode/issue/{ticket_id})
{end}"""

# Per-operation timeouts (OMN-2817 1e) - env-configurable
OPERATION_TIMEOUTS: dict[GitOperation, float] = {
    GitOperation.ADMISSION_CHECK: 30.0,
    GitOperation.BRANCH_CREATE: float(
        os.getenv("OMNICLAUDE_GIT_TIMEOUT_BRANCH_CREATE", "30")
    ),
    GitOperation.COMMIT: float(os.getenv("OMNICLAUDE_GIT_TIMEOUT_COMMIT", "30")),
    GitOperation.PUSH: float(os.getenv("OMNICLAUDE_GIT_TIMEOUT_PUSH", "60")),
    GitOperation.PR_CREATE: float(os.getenv("OMNICLAUDE_GIT_TIMEOUT_PR_CREATE", "45")),
    GitOperation.PR_UPDATE: float(os.getenv("OMNICLAUDE_GIT_TIMEOUT_PR_UPDATE", "45")),
    GitOperation.PR_CLOSE: float(os.getenv("OMNICLAUDE_GIT_TIMEOUT_PR_CLOSE", "30")),
    GitOperation.PR_MERGE: float(os.getenv("OMNICLAUDE_GIT_TIMEOUT_PR_MERGE", "60")),
    GitOperation.PR_LIST: float(os.getenv("OMNICLAUDE_GIT_TIMEOUT_PR_LIST", "45")),
    GitOperation.PR_VIEW: float(os.getenv("OMNICLAUDE_GIT_TIMEOUT_PR_VIEW", "45")),
    GitOperation.TAG_CREATE: float(
        os.getenv("OMNICLAUDE_GIT_TIMEOUT_TAG_CREATE", "60")
    ),
    GitOperation.LABEL_ADD: float(os.getenv("OMNICLAUDE_GIT_TIMEOUT_LABEL_ADD", "30")),
}

# Per-operation required fields (OMN-2817 1d)
REQUIRED_FIELDS: dict[GitOperation, list[str]] = {
    GitOperation.ADMISSION_CHECK: ["admission"],
    GitOperation.BRANCH_CREATE: ["branch_name"],
    GitOperation.COMMIT: ["commit_message"],
    GitOperation.PUSH: ["branch_name"],
    GitOperation.PR_CREATE: ["pr_title", "pr_body", "base_branch"],
    GitOperation.PR_UPDATE: ["pr_number"],
    GitOperation.PR_CLOSE: ["pr_number"],
    GitOperation.PR_MERGE: ["pr_number"],
    GitOperation.PR_LIST: ["json_fields"],
    GitOperation.PR_VIEW: ["pr_number", "json_fields"],
    GitOperation.TAG_CREATE: ["tag_name"],
    GitOperation.LABEL_ADD: ["pr_number", "labels"],
}

# Regex for extracting PR number/url from gh pr create output
_PR_URL_RE = re.compile(r"https://github\.com/[^/]+/[^/]+/pull/(\d+)")

# OMN-18782: family matches, never an override vocabulary. A citation belongs
# to the paragraph making the claim; a PR's unrelated ticket stamp credits none.
_FAILURE_CLAIM_RE = re.compile(r"\b(?:pre[-\s]?existing|unrelated)\b", re.I)
_FAILURE_WORD_RE = re.compile(
    r"\b(?:fail(?:s|ed|ing|ures?)?|errors?|broken)\b"
    r"|\b(?:CI|checks?|tests?|build)\s+(?:(?:is|are|was|were)\s+)?red\b",
    re.I,
)
_RUN_CITATION_RE = re.compile(
    r"https://github\.com/[\w.-]+/[\w.-]+/actions/runs/[1-9]\d*(?=[/#?\s)>\]]|$)"
)
_FAILURE_TICKET_RE = re.compile(r"\bOMN-[1-9]\d*\b")
_BISECT_CITATION_RE = re.compile(
    r"\b(?:bisect(?:ed|ion)?\b[^\n]*\b(?:identified|found|isolated|first bad|to)\b"
    r"[^\n]*\b[0-9a-f]{7,40}\b|[0-9a-f]{7,40}\b[^\n]*\bfirst bad commit\b)",
    re.I,
)


def pr_failure_citation_errors(body: str) -> list[str]:
    """Return actionable diagnostics for uncited failure-claim paragraphs.

    This checks citation presence, not whether evidence proves the assertion.
    Fenced examples, blockquotes and HTML comments are documentation rather
    than author assertions, and cannot supply citations to surrounding prose.
    """
    body = re.sub(r"<!--.*?-->", "", body, flags=re.S)
    prose: list[str] = []
    fence: str | None = None
    for line in body.splitlines():
        marker = re.match(r"^\s{0,3}(`{3,}|~{3,})", line)
        if fence is not None:
            if re.fullmatch(
                r"\s{0,3}" + re.escape(fence[0]) + "{" + str(len(fence)) + r",}\s*",
                line,
            ):
                fence = None
            prose.append("")
        elif marker:
            fence = marker.group(1)
            prose.append("")
        elif line.lstrip().startswith(">"):
            prose.append("")
        else:
            prose.append(line)
    errors = []
    for paragraph in re.split(r"\n\s*\n", "\n".join(prose)):
        if not (
            _FAILURE_CLAIM_RE.search(paragraph) and _FAILURE_WORD_RE.search(paragraph)
        ):
            continue
        if any(
            pattern.search(paragraph)
            for pattern in (
                _RUN_CITATION_RE,
                _BISECT_CITATION_RE,
                _FAILURE_TICKET_RE,
            )
        ):
            continue
        errors.append(
            "Failure-claim paragraph requires a run link, a bisect result with "
            "a commit, or a ticket specific to this failure:\n" + paragraph.strip()
        )
    return errors


def _citation_refusal(request: ModelGitRequest) -> ModelGitResult | None:
    errors = pr_failure_citation_errors(request.pr_body or "")
    if not errors:
        return None
    return ModelGitResult(
        operation=request.operation.value,
        status=GitResultStatus.FAILED,
        error="\n\n".join(errors),
        error_code="UNCITED_FAILURE_CLAIM",
        correlation_id=request.correlation_id,
    )


def _inject_ticket_stamp(
    body: str | None,
    ticket_id: str | None,
    correlation_id: UUID | None = None,
) -> str:
    """Inject ticket stamp if not already present. Uses HTML comment markers."""
    body = body or ""
    if TICKET_STAMP_START in body:
        return body  # Already stamped -- no duplicate
    if not ticket_id:
        return body
    stamp = TICKET_STAMP_TEMPLATE.format(
        start=TICKET_STAMP_START,
        ticket_id=ticket_id,
        end=TICKET_STAMP_END,
    )
    return body + "\n\n" + stamp


class HandlerGitSubprocess:
    """Concrete subprocess backend for git/gh CLI operations.

    Implements ProtocolGitOperations. All git/gh subprocess calls
    in the ONEX node tree MUST go through this handler.

    Targeting rules:
        - git ops: cwd=request.working_directory (fallback: process cwd)
        - gh ops: -R {request.repo} when set, else cwd + infer from remote
    """

    handler_key: str = "subprocess"

    def __init__(self) -> None:
        self._git_available: bool = False
        self._gh_available: bool = False
        self._git_version: str | None = None
        self._gh_version: str | None = None
        raw_max = os.getenv("OMNICLAUDE_GIT_MAX_CONCURRENT", "3")
        try:
            max_concurrent = max(1, int(raw_max))
        except (ValueError, TypeError):
            max_concurrent = 3
            logger.warning(
                "Invalid OMNICLAUDE_GIT_MAX_CONCURRENT=%r; using default=3",
                raw_max,
            )
        self._semaphore: asyncio.Semaphore = asyncio.Semaphore(max_concurrent)

    async def admission_check(self, request: ModelGitRequest) -> ModelGitResult:
        """Run host-local admission through this node's canonical bus route."""
        from omniclaude.nodes.node_git_effect.handlers.handler_git_admission import (
            dispatch,
        )

        validation = self._validate_request(request)
        if validation is not None:
            return validation
        if request.admission is None:
            raise ValueError("admission payload is required")
        import tempfile
        from pathlib import Path

        with tempfile.TemporaryDirectory(prefix="git-admission-") as temporary:
            result = await asyncio.to_thread(
                dispatch, request.admission, Path(temporary)
            )
        return ModelGitResult(
            operation=request.operation.value,
            status=GitResultStatus.SUCCESS,
            admission=result,
            correlation_id=request.correlation_id,
        )

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def initialize(self) -> None:
        """Probe for git/gh binary availability. Does NOT fail -- marks unavailable."""
        # Probe git
        try:
            result = subprocess.run(
                ["git", "--version"],
                capture_output=True,
                timeout=5,
                check=False,
            )
            if result.returncode == 0:
                self._git_available = True
                self._git_version = result.stdout.decode(errors="replace").strip()
            else:
                logger.warning(
                    "git --version failed (rc=%d) -- git operations disabled",
                    result.returncode,
                )
        except (FileNotFoundError, subprocess.TimeoutExpired, OSError) as exc:
            logger.warning("git probe failed (%s) -- git operations disabled", exc)

        # Probe gh
        try:
            result = subprocess.run(
                ["gh", "--version"],
                capture_output=True,
                timeout=5,
                check=False,
            )
            if result.returncode == 0:
                self._gh_available = True
                self._gh_version = result.stdout.decode(errors="replace").strip()
            else:
                logger.warning(
                    "gh --version failed (rc=%d) -- gh operations disabled",
                    result.returncode,
                )
        except (FileNotFoundError, subprocess.TimeoutExpired, OSError) as exc:
            logger.warning("gh probe failed (%s) -- gh operations disabled", exc)

        logger.info(
            "HandlerGitSubprocess initialized: git_available=%s (%s), "
            "gh_available=%s (%s), max_concurrent=%d",
            self._git_available,
            self._git_version,
            self._gh_available,
            self._gh_version,
            self._semaphore._value,
        )

    # ------------------------------------------------------------------
    # Input validation (OMN-2817 1d)
    # ------------------------------------------------------------------

    def _validate_request(self, request: ModelGitRequest) -> ModelGitResult | None:
        """Return FAILED result if required fields missing, else None."""
        required = REQUIRED_FIELDS.get(request.operation, [])
        missing = [f for f in required if getattr(request, f, None) is None]
        if missing:
            return ModelGitResult(
                operation=request.operation.value,
                status=GitResultStatus.FAILED,
                error=f"Missing required fields: {', '.join(missing)}",
                error_code="INVALID_REQUEST",
                correlation_id=request.correlation_id,
            )
        return None

    # ------------------------------------------------------------------
    # Core subprocess runners
    # ------------------------------------------------------------------

    async def _run_git(
        self, args: list[str], request: ModelGitRequest
    ) -> ModelGitResult:
        """Run a git subprocess with cwd=request.working_directory."""
        validation = self._validate_request(request)
        if validation:
            return validation
        if not self._git_available:
            return self._unavailable_result("git", request)
        timeout = OPERATION_TIMEOUTS[request.operation]
        async with self._semaphore:
            if args and args[0] == "push":
                refusal = await asyncio.to_thread(
                    ruling_reread_refusal, os.environ, request.working_directory
                )
                if refusal is not None:
                    return self._ruling_refusal_result(request, refusal)
            try:
                proc = await asyncio.create_subprocess_exec(
                    "git",
                    *args,
                    stdout=PIPE,
                    stderr=PIPE,
                    cwd=request.working_directory,
                )
            except OSError as exc:
                return ModelGitResult(
                    operation=request.operation.value,
                    status=GitResultStatus.FAILED,
                    error=f"SUBPROCESS_ERROR: {exc}",
                    error_code="SUBPROCESS_ERROR",
                    correlation_id=request.correlation_id,
                )
            try:
                stdout, stderr = await asyncio.wait_for(
                    proc.communicate(),
                    timeout=timeout,
                )
            except TimeoutError:
                try:
                    proc.kill()
                    await proc.wait()
                except (ProcessLookupError, OSError):
                    pass
                return self._timeout_result(request, timeout)

        return self._parse_git_result(request, proc.returncode, stdout, stderr)

    async def _run_gh(
        self, args: list[str], request: ModelGitRequest
    ) -> ModelGitResult:
        """Run a gh subprocess. Uses -R when request.repo is set, else cwd."""
        validation = self._validate_request(request)
        if validation:
            return validation
        if not self._gh_available:
            return self._unavailable_result("gh", request)
        full_args = list(args)
        if request.repo:
            full_args.extend(["-R", request.repo])
        timeout = OPERATION_TIMEOUTS[request.operation]
        async with self._semaphore:
            if args[:2] == ["pr", "merge"]:
                refusal = await asyncio.to_thread(
                    ruling_reread_refusal, os.environ, request.working_directory
                )
                if refusal is not None:
                    return self._ruling_refusal_result(request, refusal)
            try:
                proc = await asyncio.create_subprocess_exec(
                    "gh",
                    *full_args,
                    stdout=PIPE,
                    stderr=PIPE,
                    cwd=request.working_directory,
                )
            except OSError as exc:
                return ModelGitResult(
                    operation=request.operation.value,
                    status=GitResultStatus.FAILED,
                    error=f"SUBPROCESS_ERROR: {exc}",
                    error_code="SUBPROCESS_ERROR",
                    correlation_id=request.correlation_id,
                )
            try:
                stdout, stderr = await asyncio.wait_for(
                    proc.communicate(),
                    timeout=timeout,
                )
            except TimeoutError:
                try:
                    proc.kill()
                    await proc.wait()
                except (ProcessLookupError, OSError):
                    pass
                return self._timeout_result(request, timeout)

        return self._parse_git_result(request, proc.returncode, stdout, stderr)

    @staticmethod
    def _ruling_refusal_result(request: ModelGitRequest, reason: str) -> ModelGitResult:
        return ModelGitResult(
            operation=request.operation.value,
            status=GitResultStatus.FAILED,
            error=reason,
            error_code="LEDGER_RULING_UNACKNOWLEDGED",
            correlation_id=request.correlation_id,
        )

    async def _run_gh_json(
        self, args: list[str], request: ModelGitRequest
    ) -> ModelGitResult:
        """Run gh command expecting JSON output. Parse stdout as JSON."""
        result = await self._run_gh(args, request)
        if result.status == GitResultStatus.FAILED:
            return result
        try:
            parsed = json.loads(result.output or "")
        except (json.JSONDecodeError, TypeError):
            return ModelGitResult(
                operation=request.operation.value,
                status=GitResultStatus.FAILED,
                error=f"JSON parse failed on stdout: {(result.output or '')[:200]}",
                error_code="PARSE_ERROR",
                correlation_id=request.correlation_id,
            )
        # Return with structured data
        if request.operation == GitOperation.PR_LIST:
            if not isinstance(parsed, list):
                parsed = [parsed]
            return ModelGitResult(
                operation=request.operation.value,
                status=GitResultStatus.SUCCESS,
                output=result.output,
                pr_list=parsed,
                correlation_id=request.correlation_id,
            )
        elif request.operation == GitOperation.PR_VIEW:
            if not isinstance(parsed, dict):
                return ModelGitResult(
                    operation=request.operation.value,
                    status=GitResultStatus.FAILED,
                    error=f"Expected JSON object, got {type(parsed).__name__}",
                    error_code="PARSE_ERROR",
                    correlation_id=request.correlation_id,
                )
            return ModelGitResult(
                operation=request.operation.value,
                status=GitResultStatus.SUCCESS,
                output=result.output,
                pr_data=parsed,
                correlation_id=request.correlation_id,
            )
        return result

    # ------------------------------------------------------------------
    # Protocol methods -- existing 6
    # ------------------------------------------------------------------

    async def branch_create(self, request: ModelGitRequest) -> ModelGitResult:
        """Create a new git branch from base_ref."""
        args = ["checkout", "-b", request.branch_name or ""]
        if request.base_ref:
            args.append(request.base_ref)
        return await self._run_git(args, request)

    async def commit(self, request: ModelGitRequest) -> ModelGitResult:
        """Stage all changes and create a commit."""
        # First stage all changes
        stage_result = await self._run_git(["add", "-A"], request)
        if stage_result.status == GitResultStatus.FAILED:
            return stage_result
        # Then commit
        return await self._run_git(
            ["commit", "-m", request.commit_message or ""], request
        )

    async def push(self, request: ModelGitRequest) -> ModelGitResult:
        """Push branch to remote."""
        args = ["push", "-u", "origin", request.branch_name or ""]
        if request.force_push:
            args.insert(1, "--force-with-lease")
        return await self._run_git(args, request)

    async def pr_create(self, request: ModelGitRequest) -> ModelGitResult:
        """Create a pull request with mandatory ticket stamp block."""
        refusal = _citation_refusal(request)
        if refusal is not None:
            return refusal
        # Ticket linkage guard (OMN-6919) — warn if title has no OMN-XXXX
        if request.pr_title and not ModelGitRequest.validate_pr_title_ticket_ref(
            request.pr_title
        ):
            logger.warning(
                "PR title has no OMN-XXXX ticket reference and is not exempt: %s",
                request.pr_title,
            )
        # Inject ticket stamp (OMN-2817 1g)
        body = _inject_ticket_stamp(
            request.pr_body,
            request.ticket_id,
            request.correlation_id,
        )
        args = [
            "pr",
            "create",
            "--title",
            request.pr_title or "",
            "--body",
            body,
            "--base",
            request.base_branch or "main",
        ]
        result = await self._run_gh(args, request)
        if result.status == GitResultStatus.FAILED:
            return result
        # Extract PR URL and number from output
        output = result.output or ""
        match = _PR_URL_RE.search(output)
        pr_url = match.group(0) if match else output.strip()
        pr_number = int(match.group(1)) if match else None
        return ModelGitResult(
            operation=request.operation.value,
            status=GitResultStatus.SUCCESS,
            output=output,
            pr_url=pr_url,
            pr_number=pr_number,
            correlation_id=request.correlation_id,
        )

    async def pr_update(self, request: ModelGitRequest) -> ModelGitResult:
        """Update an existing pull request."""
        refusal = _citation_refusal(request)
        if refusal is not None:
            return refusal
        args = ["pr", "edit", str(request.pr_number or 0)]
        if request.pr_title:
            args.extend(["--title", request.pr_title])
        if request.pr_body:
            args.extend(["--body", request.pr_body])
        return await self._run_gh(args, request)

    async def pr_close(self, request: ModelGitRequest) -> ModelGitResult:
        """Close a pull request without merging."""
        args = ["pr", "close", str(request.pr_number or 0)]
        return await self._run_gh(args, request)

    # ------------------------------------------------------------------
    # Protocol methods -- new 5 (OMN-2817 1b/1h)
    # ------------------------------------------------------------------

    async def pr_merge(self, request: ModelGitRequest) -> ModelGitResult:
        """Merge a PR. If request.use_merge_queue=True, adds to MQ instead."""
        args = ["pr", "merge", str(request.pr_number or 0)]
        if request.use_merge_queue:
            args.append("--merge-queue")
        elif request.merge_method:
            method_flag = f"--{request.merge_method}"
            args.append(method_flag)
        else:
            args.append("--squash")
        result = await self._run_gh(args, request)
        if result.status == GitResultStatus.FAILED:
            return result
        merge_state = "queued" if request.use_merge_queue else "merged"
        return ModelGitResult(
            operation=request.operation.value,
            status=GitResultStatus.SUCCESS,
            output=result.output,
            merge_state=merge_state,
            correlation_id=request.correlation_id,
        )

    async def pr_list(self, request: ModelGitRequest) -> ModelGitResult:
        """List PRs. Returns structured JSON in result.pr_list."""
        json_fields = ",".join(request.json_fields or [])
        args = ["pr", "list", "--json", json_fields]
        # Apply list filters
        if request.list_filters:
            filters = request.list_filters
            if filters.state:
                args.extend(["--state", filters.state])
            if filters.head:
                args.extend(["--head", filters.head])
            if filters.base:
                args.extend(["--base", filters.base])
            if filters.author:
                args.extend(["--author", filters.author])
            if filters.label:
                args.extend(["--label", filters.label])
            if filters.search:
                args.extend(["--search", filters.search])
            args.extend(["--limit", str(filters.limit)])
        return await self._run_gh_json(args, request)

    async def pr_view(self, request: ModelGitRequest) -> ModelGitResult:
        """View single PR. Returns structured JSON in result.pr_data."""
        json_fields = ",".join(request.json_fields or [])
        args = [
            "pr",
            "view",
            str(request.pr_number or 0),
            "--json",
            json_fields,
        ]
        return await self._run_gh_json(args, request)

    async def tag_create(self, request: ModelGitRequest) -> ModelGitResult:
        """Create and push a git tag."""
        tag_name = request.tag_name or ""
        if request.tag_message:
            # Annotated tag
            tag_result = await self._run_git(
                ["tag", "-a", tag_name, "-m", request.tag_message], request
            )
        else:
            # Lightweight tag
            tag_result = await self._run_git(["tag", tag_name], request)
        if tag_result.status == GitResultStatus.FAILED:
            return tag_result
        # Push the tag
        push_result = await self._run_git(["push", "origin", tag_name], request)
        if push_result.status == GitResultStatus.FAILED:
            return push_result
        return ModelGitResult(
            operation=request.operation.value,
            status=GitResultStatus.SUCCESS,
            output=push_result.output,
            tag_name=tag_name,
            correlation_id=request.correlation_id,
        )

    async def label_add(self, request: ModelGitRequest) -> ModelGitResult:
        """Add labels to a PR."""
        labels_csv = ",".join(request.labels or [])
        args = [
            "pr",
            "edit",
            str(request.pr_number or 0),
            "--add-label",
            labels_csv,
        ]
        return await self._run_gh(args, request)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _truncate_output(raw: bytes) -> str:
        """Decode and truncate stdout to ``_MAX_OUTPUT_BYTES``."""
        if len(raw) > _MAX_OUTPUT_BYTES:
            truncated = raw[:_MAX_OUTPUT_BYTES].decode(errors="replace")
            return truncated + _TRUNCATION_MARKER
        return raw.decode(errors="replace")

    @staticmethod
    def _stderr_tail(raw: bytes) -> str:
        """Return the last ``_STDERR_TAIL_BYTES`` of stderr, decoded."""
        if not raw:
            return ""
        tail = raw[-_STDERR_TAIL_BYTES:]
        return tail.decode(errors="replace")

    def _parse_git_result(
        self,
        request: ModelGitRequest,
        returncode: int | None,
        stdout: bytes,
        stderr: bytes,
    ) -> ModelGitResult:
        """Build a ModelGitResult from subprocess output."""
        stdout_text = self._truncate_output(stdout)
        if returncode != 0:
            stderr_tail = self._stderr_tail(stderr)
            error_code = self._classify_error(stderr_tail, returncode)
            return ModelGitResult(
                operation=request.operation.value,
                status=GitResultStatus.FAILED,
                output=stdout_text if stdout_text else None,
                error=(
                    f"SUBPROCESS_ERROR: exit code {returncode}"
                    f"{f' -- stderr: {stderr_tail}' if stderr_tail else ''}"
                ),
                error_code=error_code,
                correlation_id=request.correlation_id,
            )
        return ModelGitResult(
            operation=request.operation.value,
            status=GitResultStatus.SUCCESS,
            output=stdout_text if stdout_text else None,
            correlation_id=request.correlation_id,
        )

    @staticmethod
    def _classify_error(
        stderr: str,
        returncode: int | None,  # noqa: ARG004
    ) -> str:
        """Classify error from stderr content into a machine-readable error code.

        Args:
            stderr: Decoded stderr content from the subprocess.
            returncode: Process exit code (reserved for future use).
        """
        stderr_lower = stderr.lower()
        if "authentication" in stderr_lower or "credential" in stderr_lower:
            return "AUTH_FAILURE"
        if "conflict" in stderr_lower or "merge conflict" in stderr_lower:
            return "CONFLICT"
        if "not found" in stderr_lower or "no such" in stderr_lower:
            return "NOT_FOUND"
        return "SUBPROCESS_ERROR"

    def _unavailable_result(
        self, binary: str, request: ModelGitRequest
    ) -> ModelGitResult:
        """Return a FAILED result indicating a binary is unavailable."""
        error_code = "GIT_UNAVAILABLE" if binary == "git" else "GH_UNAVAILABLE"
        return ModelGitResult(
            operation=request.operation.value,
            status=GitResultStatus.FAILED,
            error=f"{error_code}: {binary} CLI is not available",
            error_code=error_code,
            correlation_id=request.correlation_id,
        )

    @staticmethod
    def _timeout_result(request: ModelGitRequest, timeout: float) -> ModelGitResult:
        """Return a FAILED result for a timed-out operation."""
        return ModelGitResult(
            operation=request.operation.value,
            status=GitResultStatus.FAILED,
            error=f"TIMEOUT: operation exceeded {timeout}s deadline",
            error_code="TIMEOUT",
            correlation_id=request.correlation_id,
        )
