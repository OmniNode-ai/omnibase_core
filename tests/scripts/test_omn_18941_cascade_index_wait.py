# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""OMN-18941 -- wait for the released version before resolving a cascade lock.

After rewriting an exact pin, the cascade could run ``uv lock`` before PyPI
listed the just-uploaded version and fail with "there is no version of
omnibase-core==0.47.29". Execute the workflow's actual Bash under GitHub's
errexit/pipefail settings against a local simple-index stub to pin the wait,
its elapsed-time telemetry, exact filename matching, and cache-defeating polls.
The subsequent lock must explicitly refresh uv's own package HTTP cache.
"""

from __future__ import annotations

import json
import re
import subprocess
import time
from collections.abc import Iterator
from dataclasses import dataclass, field
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from threading import Thread
from typing import Literal
from urllib.parse import urlsplit

import pytest
import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]
WORKFLOW_PATH = REPO_ROOT / ".github" / "workflows" / "dependency-cascade.yml"

_JOB_NAME = "open-bump-pr"
_WAIT_STEP_NAME = "Wait for released version on the index (OMN-18941)"
_ACCEPT = "application/vnd.pypi.simple.v1+json"
_Mode = Literal["never", "after-delay", "always", "only-other-versions"]


def _steps() -> list[dict[str, object]]:
    with WORKFLOW_PATH.open() as handle:
        document = yaml.safe_load(handle)
    steps = document["jobs"][_JOB_NAME]["steps"]
    assert isinstance(steps, list)
    return [step for step in steps if isinstance(step, dict)]


def _step(name: str) -> dict[str, object]:
    for step in _steps():
        if step.get("name") == name:
            return step
    raise AssertionError(f"job {_JOB_NAME!r} has no step named {name!r}")


@dataclass
class _Request:
    path: str
    accept: str | None
    cache_control: str | None
    pragma: str | None


@dataclass
class _IndexStub:
    mode: _Mode = "never"
    delay_s: float = 2.5
    started_at: float = field(default_factory=time.monotonic)
    index_base: str = ""
    requests: list[_Request] = field(default_factory=list)

    def body(self) -> bytes:
        present = self.mode == "always" or (
            self.mode == "after-delay"
            and time.monotonic() - self.started_at >= self.delay_s
        )
        filenames: list[str] = []
        if present:
            filenames = [
                "omnibase_core-0.47.29-py3-none-any.whl",
                "omnibase_core-0.47.29.tar.gz",
            ]
        elif self.mode == "only-other-versions":
            filenames = [
                "omnibase_core-0.47.2-py3-none-any.whl",
                "omnibase_core-0.47.28.tar.gz",
            ]
        payload = {
            "name": "omnibase-core",
            "files": [{"filename": filename} for filename in filenames],
            "versions": ["0.47.29"] if present else [],
        }
        # Cover both compact PyPI JSON and spaced filename fields.
        separators = (",", ":") if self.mode == "always" else (", ", ": ")
        return json.dumps(payload, separators=separators).encode()


@pytest.fixture
def index_stub() -> Iterator[_IndexStub]:
    stub = _IndexStub()

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args: object, **kwargs: object) -> None:
            pass

        def do_GET(self) -> None:
            stub.requests.append(
                _Request(
                    path=self.path,
                    accept=self.headers.get("Accept"),
                    cache_control=self.headers.get("Cache-Control"),
                    pragma=self.headers.get("Pragma"),
                )
            )
            if urlsplit(self.path).path != "/simple/omnibase-core/":
                self.send_error(404)
                return
            body = stub.body()
            self.send_response(200)
            self.send_header("Content-Type", _ACCEPT)
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    stub.index_base = f"http://127.0.0.1:{server.server_port}/simple"
    thread = Thread(
        target=server.serve_forever, kwargs={"poll_interval": 0.05}, daemon=True
    )
    thread.start()
    try:
        yield stub
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


def _assert_requests(stub: _IndexStub) -> None:
    assert stub.requests, "the wait must poll the index"
    queries: list[str] = []
    for request in stub.requests:
        parsed = urlsplit(request.path)
        assert parsed.path == "/simple/omnibase-core/"
        assert parsed.query
        queries.append(parsed.query)
        assert request.accept == _ACCEPT
        assert request.cache_control == "no-cache"
        assert request.pragma == "no-cache"
    assert len(set(queries)) == len(queries), "each poll must defeat index caches"


def _run_wait(
    tmp_path: Path, stub: _IndexStub, *, total_s: int = 3
) -> subprocess.CompletedProcess[str]:
    run = _step(_WAIT_STEP_NAME).get("run", "")
    assert isinstance(run, str)
    assert "${{" not in run
    script = tmp_path / "wait.sh"
    script.write_text(run)
    stub.started_at = time.monotonic()
    # `env` applies the step's variables on top of the inherited environment, so
    # the test reads no process environment of its own.
    result = subprocess.run(
        [
            "env",
            "PKG_HYPHEN=omnibase-core",
            "RESOLVED=0.47.29",
            f"CASCADE_INDEX_BASE={stub.index_base}",
            "CASCADE_WAIT_INTERVAL_S=1",
            f"CASCADE_WAIT_TOTAL_S={total_s}",
            "bash",
            "--noprofile",
            "--norc",
            "-eo",
            "pipefail",
            str(script),
        ],
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )
    _assert_requests(stub)
    return result


def _waited_s(result: subprocess.CompletedProcess[str], token: str) -> int:
    match = re.search(
        rf"^{token} package=omnibase-core version=0\.47\.29 waited_s=(\d+)$",
        result.stdout,
        re.MULTILINE,
    )
    assert match is not None, (result.stdout, result.stderr)
    return int(match.group(1))


@pytest.mark.unit
@pytest.mark.parametrize("mode", ["never", "only-other-versions"])
def test_unlisted_exact_version_times_out(
    tmp_path: Path, index_stub: _IndexStub, mode: _Mode
) -> None:
    """An absent version or a filename with only a version prefix cannot pass."""
    index_stub.mode = mode
    result = _run_wait(tmp_path, index_stub)
    assert result.returncode != 0
    assert _waited_s(result, "CASCADE-INDEX-WAIT-TIMEOUT") >= 3
    assert "::error::" in result.stdout
    assert len(index_stub.requests) > 1


@pytest.mark.unit
def test_version_appearing_after_propagation_wait_succeeds(
    tmp_path: Path, index_stub: _IndexStub
) -> None:
    index_stub.mode = "after-delay"
    result = _run_wait(tmp_path, index_stub, total_s=15)
    assert result.returncode == 0, (result.stdout, result.stderr)
    assert _waited_s(result, "CASCADE-INDEX-WAIT-OK") > 0
    assert "Not listed yet" in result.stdout
    assert len(index_stub.requests) > 1


@pytest.mark.unit
def test_version_present_immediately_reports_zero_wait(
    tmp_path: Path, index_stub: _IndexStub
) -> None:
    index_stub.mode = "always"
    result = _run_wait(tmp_path, index_stub)
    assert result.returncode == 0, (result.stdout, result.stderr)
    assert _waited_s(result, "CASCADE-INDEX-WAIT-OK") == 0
    assert len(index_stub.requests) == 1


@pytest.mark.unit
def test_wait_precedes_lock_and_lock_refreshes_the_package() -> None:
    steps = _steps()
    names = [step.get("name") for step in steps]
    wait_index = names.index(_WAIT_STEP_NAME)
    lock_index = names.index("Upgrade lockfile")
    assert wait_index < lock_index
    wait = _step(_WAIT_STEP_NAME)
    assert wait.get("if") == "steps.token_check.outputs.has_token == 'true'"
    assert wait.get("env") == {
        "PKG_HYPHEN": "${{ steps.vars.outputs.pkg_hyphen }}",
        "RESOLVED": "${{ steps.vars.outputs.version }}",
    }
    run = _step("Upgrade lockfile").get("run", "")
    assert isinstance(run, str)
    lock_line = next(
        line.strip() for line in run.splitlines() if line.strip().startswith("uv lock")
    )
    assert '--refresh-package "$BUMP_PACKAGE"' in lock_line
