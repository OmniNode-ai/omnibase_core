# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""Guards that the PGDG key fetch in receipt-gate retries every error."""

from __future__ import annotations

import re
import shlex
import shutil
import socket
import subprocess
import threading
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest
import yaml

pytestmark = pytest.mark.unit

WORKFLOW_PATH = (
    Path(__file__).resolve().parents[2] / ".github" / "workflows" / "receipt-gate.yml"
)
PG_TOOLS_STEP = "Provide the PostgreSQL 16 server tools"


def _workflow() -> dict[Any, Any]:
    data = yaml.safe_load(WORKFLOW_PATH.read_text())
    assert isinstance(data, dict)
    return data


def _job() -> dict[str, Any]:
    return _workflow()["jobs"]["dod-verify"]


def _step(name: str) -> dict[str, Any]:
    return next(step for step in _job()["steps"] if step.get("name") == name)


def _pgdg_key_argv() -> list[str]:
    script = _step(PG_TOOLS_STEP)["run"]
    match = re.search(r"curl\s+[^\n]*ACCC4CF8\.asc[^\n]*?-o\s+\"[^\"]*\"", script)
    assert match is not None, "the PGDG key curl invocation is missing from the step"
    return shlex.split(match.group(0))


def test_pgdg_key_fetch_retries_every_error() -> None:
    argv = _pgdg_key_argv()
    assert "--retry-all-errors" in argv
    assert "--retry-delay" in argv
    assert "--retry-max-time" in argv


def test_every_curl_in_the_workflow_retries_every_error() -> None:
    workflow = _workflow()
    found = 0
    for job in workflow["jobs"].values():
        for step in job.get("steps", []):
            script = step.get("run", "")
            for line in script.splitlines():
                stripped = line.strip()
                if stripped.startswith("#"):
                    continue
                if "curl " not in stripped:
                    continue
                found += 1
                assert "--retry-all-errors" in stripped, (
                    f"curl in step {step.get('name')!r} lacks --retry-all-errors: {stripped}"
                )
    assert found >= 1, "no curl command was found in the workflow"


@pytest.fixture
def drop_first_server() -> Iterator[tuple[int, list[int]]]:
    """A 127.0.0.1 server that drops the first connection and serves the rest."""
    connections: list[int] = []
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind(("127.0.0.1", 0))
    server.listen(16)
    port = server.getsockname()[1]

    def _serve() -> None:
        try:
            while True:
                try:
                    conn, _ = server.accept()
                except OSError:  # listening socket closed: stop serving
                    break
                connections.append(len(connections))
                if len(connections) == 1:
                    conn.close()
                    continue
                try:
                    conn.recv(65536)
                    conn.sendall(b"HTTP/1.1 200 OK\r\nContent-Length: 3\r\n\r\nkey")
                except OSError:  # client already gone; nothing to answer
                    pass
                finally:
                    conn.close()
        except OSError:
            pass

    thread = threading.Thread(target=_serve, daemon=True)
    thread.start()
    try:
        yield port, connections
    finally:
        server.close()
        thread.join(timeout=5)


@pytest.mark.skipif(shutil.which("curl") is None, reason="curl is required")
def test_pgdg_key_fetch_survives_a_dropped_connection(
    tmp_path: Path, drop_first_server: tuple[int, list[int]]
) -> None:
    port, _ = drop_first_server
    argv = _pgdg_key_argv()
    out_file = tmp_path / "pgdg.asc"
    new_argv: list[str] = []
    skip_next = False
    for token in argv:
        if skip_next:
            skip_next = False
            continue
        if token == "--retry-delay":
            new_argv.append(token)
            new_argv.append("1")
            skip_next = True
            continue
        if token.startswith("https://") and token.endswith("ACCC4CF8.asc"):
            new_argv.append(f"http://127.0.0.1:{port}/")
            continue
        if token == "-o":
            new_argv.append(token)
            new_argv.append(str(out_file))
            skip_next = True
            continue
        new_argv.append(token)
    result = subprocess.run(
        new_argv, capture_output=True, text=True, timeout=60, check=False
    )
    assert result.returncode == 0, result.stderr
    assert out_file.read_bytes() == b"key"


@pytest.mark.skipif(shutil.which("curl") is None, reason="curl is required")
def test_old_retry_flags_fail_on_a_dropped_connection(
    tmp_path: Path, drop_first_server: tuple[int, list[int]]
) -> None:
    port, connections = drop_first_server
    out_file = tmp_path / "pgdg.asc"
    result = subprocess.run(
        [
            "curl",
            "-fsSL",
            "--retry",
            "3",
            f"http://127.0.0.1:{port}/",
            "-o",
            str(out_file),
        ],
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
    )
    assert result.returncode != 0, result.stderr
    assert len(connections) == 1, (
        f"expected exactly one connection, saw {len(connections)}"
    )
