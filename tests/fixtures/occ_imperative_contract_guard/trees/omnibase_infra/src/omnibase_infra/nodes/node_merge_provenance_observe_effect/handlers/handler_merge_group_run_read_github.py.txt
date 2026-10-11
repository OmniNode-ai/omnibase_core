# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""GitHub REST binding of ProtocolMergeGroupRunReader (OMN-19927).

The EFFECT handler that owns this node's only external I/O.

Two reads, both paginated to their ``total_count``:

* ``GET /repos/{repo}/actions/runs?head_sha={sha}&event=merge_group``
* ``GET /repos/{repo}/actions/runs/{run_id}/jobs?filter=latest``

Any HTTP error, malformed payload, or a page sequence that ends short of the
reported ``total_count`` raises ``MergeGroupReadError``. The effect handler
turns that into ``read_ok=False``; it is never flattened into an empty list.
"""

from __future__ import annotations

import json
import urllib.error
import urllib.parse
import urllib.request
from collections.abc import Callable

from omnibase_infra.enums import EnumHandlerType, EnumHandlerTypeCategory
from omnibase_infra.nodes.node_merge_provenance_observe_effect.models.model_workflow_job_fact import (
    ModelWorkflowJobFact,
)
from omnibase_infra.nodes.node_merge_provenance_observe_effect.models.model_workflow_run_fact import (
    ModelWorkflowRunFact,
)

_PER_PAGE = 100
# A merge group re-queued this many times for one sha, or a CI run with this
# many jobs, is outside anything measured; stop and report rather than loop.
_MAX_PAGES = 10


def _workflow_path(raw: object) -> str:
    """The workflow file path without a ``@<ref>`` suffix.

    The runs API returns ``.github/workflows/ci.yml`` for this repository
    (read 2026-09-28 on run 36409772437), but documents ``path@ref`` for
    some runs; both forms name the same workflow file.
    """
    if not isinstance(raw, str) or not raw:
        raise ValueError(f"workflow run path is not a non-empty string: {raw!r}")
    return raw.split("@", 1)[0]


class MergeGroupReadError(RuntimeError):
    """A read of the Actions API failed or came back incomplete."""


Fetch = Callable[[str], dict[str, object]]


class HandlerMergeGroupRunReadGithub:
    """Reads merge-group runs and their jobs from the GitHub REST API."""

    def __init__(
        self,
        token: str,
        *,
        api_url: str = "https://api.github.com",  # url-authority-ok: the public GitHub REST API base; GitHub Enterprise callers pass their own
        timeout_seconds: float = 30.0,
        fetch: Fetch | None = None,
    ) -> None:
        if not token:
            raise MergeGroupReadError("no GitHub token supplied")
        self._token = token
        self._api_url = api_url.rstrip("/")
        self._timeout = timeout_seconds
        self._fetch: Fetch = fetch or self._http_get

    @property
    def handler_type(self) -> EnumHandlerType:
        return EnumHandlerType.INFRA_HANDLER

    @property
    def handler_category(self) -> EnumHandlerTypeCategory:
        return EnumHandlerTypeCategory.EFFECT

    def _http_get(self, path_and_query: str) -> dict[str, object]:
        request = urllib.request.Request(  # noqa: S310 -- fixed https API base
            f"{self._api_url}{path_and_query}",
            headers={
                "Accept": "application/vnd.github+json",
                "Authorization": f"Bearer {self._token}",
                "X-GitHub-Api-Version": "2022-11-28",
            },
        )
        try:
            with urllib.request.urlopen(request, timeout=self._timeout) as response:  # noqa: S310
                payload = json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            raise MergeGroupReadError(f"HTTP {exc.code} on {path_and_query}") from exc
        except (urllib.error.URLError, TimeoutError, OSError, ValueError) as exc:
            raise MergeGroupReadError(
                f"{type(exc).__name__} on {path_and_query}: {exc}"
            ) from exc
        if not isinstance(payload, dict):
            raise MergeGroupReadError(f"non-object payload on {path_and_query}")
        return payload

    def _paginate(self, base: str, key: str) -> list[dict[str, object]]:
        items: list[dict[str, object]] = []
        total: int | None = None
        for page in range(1, _MAX_PAGES + 1):
            sep = "&" if "?" in base else "?"
            payload = self._fetch(f"{base}{sep}per_page={_PER_PAGE}&page={page}")
            raw_total = payload.get("total_count")
            raw_items = payload.get(key)
            if not isinstance(raw_total, int) or not isinstance(raw_items, list):
                raise MergeGroupReadError(f"malformed {key} page {page} on {base}")
            total = raw_total
            items.extend(i for i in raw_items if isinstance(i, dict))
            if len(items) >= total or not raw_items:
                break
        if total is None or len(items) < total:
            raise MergeGroupReadError(
                f"read {len(items)} of {total} {key} on {base}; refusing a short list"
            )
        return items

    def list_merge_group_runs(
        self, repository: str, head_sha: str
    ) -> list[ModelWorkflowRunFact]:
        query = urllib.parse.urlencode({"head_sha": head_sha, "event": "merge_group"})
        rows = self._paginate(
            f"/repos/{repository}/actions/runs?{query}", "workflow_runs"
        )
        try:
            return [
                ModelWorkflowRunFact(
                    run_id=row["id"],
                    run_attempt=row.get("run_attempt") or 1,
                    event=row["event"],
                    head_sha=row["head_sha"],
                    head_branch=row.get("head_branch") or "",
                    workflow_path=_workflow_path(row["path"]),
                    status=row["status"],
                    conclusion=row.get("conclusion"),
                )
                for row in rows
            ]
        except (KeyError, ValueError) as exc:
            raise MergeGroupReadError(f"malformed workflow run: {exc}") from exc

    def list_latest_attempt_jobs(
        self, repository: str, run_id: int
    ) -> list[ModelWorkflowJobFact]:
        rows = self._paginate(
            f"/repos/{repository}/actions/runs/{run_id}/jobs?filter=latest", "jobs"
        )
        try:
            return [
                ModelWorkflowJobFact(
                    name=row["name"],
                    status=row["status"],
                    conclusion=row.get("conclusion"),
                )
                for row in rows
            ]
        except (KeyError, ValueError) as exc:
            raise MergeGroupReadError(f"malformed job: {exc}") from exc


__all__: list[str] = ["HandlerMergeGroupRunReadGithub", "MergeGroupReadError"]
