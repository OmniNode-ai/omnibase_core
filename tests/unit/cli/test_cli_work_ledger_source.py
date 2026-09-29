# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""RED acceptance tests for the work ledger projection read surface."""

from __future__ import annotations

import json
import re
import socket
import threading
import uuid
from collections.abc import Iterator
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

import pytest

from omnibase_core.enums.enum_hold_block import EnumHoldBlock
from omnibase_core.models.events.work import (
    WORK_LEDGER_SCHEMA,
    ModelHoldScope,
    ModelPrKey,
    ModelRecipients,
    ModelSessionActor,
    ModelWorkClaimRequested,
    ModelWorkEvent,
    ModelWorkHoldPlaced,
    ModelWorkLedgerEpochOpened,
    ModelWorkLedgerRecord,
    ModelWorkMessageSent,
    dump_work_ledger_line,
)
from omnibase_core.nodes.node_work_ledger_state_compute.runtime_work_ledger import (
    main,
)

pytestmark = pytest.mark.unit

PATH_ENV = "ONEX_WORK_LEDGER_PATH"
PROJECTION_ENV = "ONEX_WORK_LEDGER_PROJECTION_URL"
TOPIC = "onex.snapshot.projection.work.ledger.v1"
HEADER = re.compile(
    r"^ledger=(?P<path>\S+) sha256=(?P<sha>[0-9a-f]{64}|none) "
    r"lines=(?P<lines>\d+) epoch=(?P<epoch>[0-9a-f-]{36}|none)$"
)
T0 = datetime(2026, 9, 24, 12, 0, 0, tzinfo=UTC)
EPOCH_ID = uuid.UUID("eeeeeeee-eeee-4eee-8eee-eeeeeeeeeeee")
HOLD_ID = uuid.UUID("00000000-0000-4000-8000-000000000001")
PAUSE_ID = uuid.UUID("00000000-0000-4000-8000-000000000002")
LEASE_ID = uuid.UUID("00000000-0000-4000-8000-000000000003")
CLAIM_ID = uuid.UUID("00000000-0000-4000-8000-000000000004")
MESSAGE_ID = uuid.UUID("00000000-0000-4000-8000-000000000005")
HELD = ["held", "--repo", "omnibase_infra", "--pr", "4005", "--action", "merge"]
CLEAR = ["held", "--repo", "omnibase_infra", "--pr", "1", "--action", "merge"]


def _actor(lane: str) -> ModelSessionActor:
    return ModelSessionActor(session_handle=lane, agent_kind="build-lane")


def _line(event: ModelWorkEvent) -> str:
    return dump_work_ledger_line(
        ModelWorkLedgerRecord.model_validate(
            {"schema": WORK_LEDGER_SCHEMA, "event": event}
        )
    )


def _epoch() -> ModelWorkLedgerEpochOpened:
    return ModelWorkLedgerEpochOpened(
        event_id=EPOCH_ID,
        emitted_at=T0,
        actor=_actor("ledger-tool"),
        summary="cutover epoch",
        reason="cutover",
        epoch_seq=0,
        archived_path="docs/tracking/archive/ROLLING_WORK_LEDGER_PRE_TYPED.md",
        archived_sha256="0" * 64,
        archived_line_count=10,
        review_list_ref="beta/tracking/typed-ledger-cutover-review.md",
    )


def _claim() -> ModelWorkClaimRequested:
    return ModelWorkClaimRequested(
        event_id=CLAIM_ID,
        emitted_at=T0,
        actor=_actor("lane-a"),
        summary="claim",
        ticket_id="OMN-1",
        prs=frozenset({ModelPrKey(repo="omnibase_infra", number=4005)}),
    )


def _hold(*, summary: str = "hold one PR") -> ModelWorkHoldPlaced:
    return ModelWorkHoldPlaced(
        event_id=HOLD_ID,
        emitted_at=T0,
        actor=_actor("lane-a"),
        summary=summary,
        scope=ModelHoldScope(
            prs=frozenset({ModelPrKey(repo="omnibase_infra", number=4005)})
        ),
        blocks=frozenset({EnumHoldBlock.MERGE}),
    )


def _events() -> list[ModelWorkEvent]:
    return [
        _epoch(),
        _hold(),
        ModelWorkHoldPlaced(
            event_id=PAUSE_ID,
            emitted_at=T0,
            actor=_actor("lane-a"),
            summary="runtime merge pause",
            scope=ModelHoldScope(repos=frozenset({"omnimarket"})),
            blocks=frozenset({EnumHoldBlock.MERGE, EnumHoldBlock.ARM}),
            runtime_only=True,
        ),
        ModelWorkHoldPlaced(
            event_id=LEASE_ID,
            emitted_at=T0,
            actor=_actor("lane-a"),
            summary="lease",
            scope=ModelHoldScope(surfaces=frozenset({"dogfood-105"})),
            blocks=frozenset({EnumHoldBlock.DISPATCH}),
            expires_at=datetime.now(UTC) + timedelta(days=365),
        ),
        _claim(),
        ModelWorkMessageSent(
            event_id=MESSAGE_ID,
            emitted_at=T0,
            actor=_actor("lane-a"),
            summary="message",
            to=ModelRecipients(lanes=frozenset({"lane-c"})),
        ),
    ]


def _write(path: Path, lines: list[str]) -> Path:
    path.write_text("".join(f"{line}\n" for line in lines), encoding="utf-8")
    return path


def _rows(events: list[ModelWorkEvent]) -> list[dict[str, str]]:
    return [
        {"event_id": str(event.event_id), "record": _line(event)} for event in events
    ]


def _call(
    args: list[str],
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    local: Path | None = None,
) -> tuple[int, str]:
    if local is None:
        monkeypatch.delenv(PATH_ENV, raising=False)
    else:
        monkeypatch.setenv(PATH_ENV, str(local))
    try:
        code = main(args)
    except SystemExit as exc:
        assert isinstance(exc.code, int)
        code = exc.code
    return code, capsys.readouterr().out


@dataclass
class ProjectionServer:
    server: ThreadingHTTPServer
    thread: threading.Thread
    rows: list[dict[str, str]] = field(default_factory=list)
    staleness: dict[str, object] = field(
        default_factory=lambda: {
            "stale": False,
            "applied_offset": 42,
            "end_offset": 45,
            "lag_records": 3,
            "last_applied_event_at": T0.isoformat(),
        }
    )
    status: int = 200
    body_override: bytes | None = None
    page_size: int | None = None
    paths: list[str] = field(default_factory=list)

    @property
    def url(self) -> str:
        port = self.server.server_address[1]
        return f"http://127.0.0.1:{port}"


@pytest.fixture
def projection() -> Iterator[ProjectionServer]:
    state: ProjectionServer

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:
            state.paths.append(self.path)
            parsed = urlsplit(self.path)
            query = parse_qs(parsed.query)
            cursor = int(query.get("cursor", ["0"])[0])
            requested = int(query.get("limit", ["100"])[0])
            size = min(requested, state.page_size or requested)
            page = state.rows[cursor : cursor + size]
            next_cursor = (
                str(cursor + size) if cursor + size < len(state.rows) else None
            )
            payload = {
                "rows": page,
                "next_cursor": next_cursor,
                "truncated": next_cursor is not None,
                "staleness": state.staleness,
            }
            body = state.body_override
            if body is None:
                body = (
                    b'{"error":"unknown_topic"}'
                    if state.status == 404
                    else json.dumps(payload).encode("utf-8")
                )
            self.send_response(state.status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, message: str, *args: object) -> None:
            pass

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    state = ProjectionServer(server=server, thread=thread)
    thread.start()
    try:
        yield state
    finally:
        server.shutdown()
        thread.join()
        server.server_close()


def _unreachable_url() -> str:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        port = sock.getsockname()[1]
    return f"http://127.0.0.1:{port}"


def _assert_verdict(code: int, out: str, expected: int, verdict: str) -> None:
    lines = out.splitlines()
    assert len(lines) >= 2, out
    assert lines[0].startswith("ledger="), out
    assert lines[1].startswith(f"verdict={verdict} "), out
    assert code == expected, out


def test_probe_projection_held_cites_hold_and_watermark(
    projection: ProjectionServer,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    projection.rows = _rows(_events())
    monkeypatch.setenv(PROJECTION_ENV, projection.url)
    code, out = _call(["--source", "projection", *HELD], monkeypatch, capsys)
    _assert_verdict(code, out, 3, "held")
    assert " source=projection watermark=42/45 lag=3" in out.splitlines()[0]
    assert f"hold event={HOLD_ID}" in out
    assert projection.paths
    assert all(f"/projection/{TOPIC}?limit=" in path for path in projection.paths)


def test_probe_projection_not_held_is_clear(
    projection: ProjectionServer,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    projection.rows = _rows(_events())
    monkeypatch.setenv(PROJECTION_ENV, projection.url)
    code, out = _call([*CLEAR, "--source", "projection"], monkeypatch, capsys)
    _assert_verdict(code, out, 0, "clear")
    assert " source=projection watermark=42/45 lag=3" in out.splitlines()[0]


def test_probe_projection_paging_preserves_verdict(
    projection: ProjectionServer,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    projection.rows = _rows(_events()[:3])
    monkeypatch.setenv(PROJECTION_ENV, projection.url)
    one_code, one_out = _call([*HELD, "--source", "projection"], monkeypatch, capsys)
    projection.paths.clear()
    projection.page_size = 2
    page_code, page_out = _call([*HELD, "--source", "projection"], monkeypatch, capsys)
    _assert_verdict(page_code, page_out, 3, "held")
    assert one_code == page_code
    assert one_out.splitlines()[1:] == page_out.splitlines()[1:]
    assert len(projection.paths) == 2
    assert "cursor=" in projection.paths[1]


@pytest.mark.parametrize(
    ("missing_epoch", "expected", "verdict"),
    [(False, 0, "clear"), (True, 2, "undecided")],
)
def test_probe_projection_health_has_watermark(
    projection: ProjectionServer,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    missing_epoch: bool,
    expected: int,
    verdict: str,
) -> None:
    projection.rows = _rows([_claim()] if missing_epoch else _events())
    monkeypatch.setenv(PROJECTION_ENV, projection.url)
    code, out = _call(["health", "--source", "projection"], monkeypatch, capsys)
    _assert_verdict(code, out, expected, verdict)
    assert "query=health" in out.splitlines()[1]
    assert " source=projection watermark=42/45 lag=3" in out.splitlines()[0]


def test_probe_stale_projection_is_undecided(
    projection: ProjectionServer,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    projection.rows = _rows(_events())
    projection.staleness["stale"] = True
    monkeypatch.setenv(PROJECTION_ENV, projection.url)
    code, out = _call([*CLEAR, "--source", "projection"], monkeypatch, capsys)
    _assert_verdict(code, out, 2, "undecided")
    assert out.splitlines()[0].endswith(" source=projection")
    assert any(line.startswith("reason=projection") for line in out.splitlines())


def test_probe_unknown_topic_is_undecided(
    projection: ProjectionServer,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    projection.status = 404
    monkeypatch.setenv(PROJECTION_ENV, projection.url)
    code, out = _call([*CLEAR, "--source", "projection"], monkeypatch, capsys)
    _assert_verdict(code, out, 2, "undecided")
    assert out.splitlines()[0].endswith(" source=projection")
    reasons = [
        line for line in out.splitlines() if line.startswith("reason=projection")
    ]
    assert len(reasons) == 1
    assert "404" in reasons[0] or "unknown_topic" in reasons[0]


_NO_PAGINATION = (
    b'{"rows":[],"staleness":{"stale":false,"applied_offset":1,"end_offset":1,'
    b'"lag_records":0}}'
)


@pytest.mark.parametrize(
    "body",
    [b"not json", b'{"rows":[]}', _NO_PAGINATION],
    ids=["json", "keys", "paging"],
)
def test_probe_bad_projection_body_is_undecided(
    projection: ProjectionServer,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    body: bytes,
) -> None:
    projection.body_override = body
    monkeypatch.setenv(PROJECTION_ENV, projection.url)
    code, out = _call([*CLEAR, "--source", "projection"], monkeypatch, capsys)
    _assert_verdict(code, out, 2, "undecided")
    assert out.splitlines()[0].endswith(" source=projection")
    assert any(line.startswith("reason=projection") for line in out.splitlines())


def test_probe_conflicting_duplicate_in_union_is_undecided(
    projection: ProjectionServer,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    projection.rows = _rows([_epoch(), _hold()])
    local = _write(tmp_path / "local.jsonl", [_line(_hold(summary="different hold"))])
    monkeypatch.setenv(PROJECTION_ENV, projection.url)
    code, out = _call([*HELD, "--source", "auto"], monkeypatch, capsys, local)
    _assert_verdict(code, out, 2, "undecided")
    assert " source=union" in out.splitlines()[0]
    assert any(line.startswith("reason=") for line in out.splitlines())


@pytest.mark.parametrize(
    ("query", "expected", "verdict"), [(HELD, 3, "held"), (CLEAR, 0, "clear")]
)
def test_fallback_unreachable_uses_local_answer(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    query: list[str],
    expected: int,
    verdict: str,
) -> None:
    local = _write(tmp_path / "local.jsonl", [_line(event) for event in _events()])
    monkeypatch.setenv(PROJECTION_ENV, _unreachable_url())
    local_code, local_out = _call(
        [*query, "--source", "local"], monkeypatch, capsys, local
    )
    auto_code, auto_out = _call(
        [*query, "--source", "auto"], monkeypatch, capsys, local
    )
    _assert_verdict(local_code, local_out, expected, verdict)
    _assert_verdict(auto_code, auto_out, expected, verdict)
    assert " source=local" in local_out.splitlines()[0]
    assert auto_out.splitlines()[0].endswith(" source=local-only")
    assert local_out.splitlines()[1:] == auto_out.splitlines()[1:]


@pytest.mark.parametrize("fault", ["stale", "404", "bad-json", "missing-keys"])
def test_fallback_projection_fault_uses_local_buffer(
    projection: ProjectionServer,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    fault: str,
) -> None:
    projection.rows = _rows(_events())
    if fault == "stale":
        projection.staleness["stale"] = True
    elif fault == "404":
        projection.status = 404
    elif fault == "bad-json":
        projection.body_override = b"not json"
    else:
        projection.body_override = b'{"rows":[]}'
    local = _write(tmp_path / "local.jsonl", [_line(event) for event in _events()])
    monkeypatch.setenv(PROJECTION_ENV, projection.url)
    code, out = _call([*HELD, "--source", "auto"], monkeypatch, capsys, local)
    _assert_verdict(code, out, 3, "held")
    assert out.splitlines()[0].endswith(" source=local-only")
    assert f"hold event={HOLD_ID}" in out


@pytest.mark.parametrize("missing_path", [False, True])
def test_fallback_unreachable_and_absent_local_is_unavailable(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    missing_path: bool,
) -> None:
    monkeypatch.setenv(PROJECTION_ENV, _unreachable_url())
    local = tmp_path / "missing.jsonl" if missing_path else None
    code, out = _call([*CLEAR, "--source", "auto"], monkeypatch, capsys, local)
    _assert_verdict(code, out, 2, "undecided")
    assert out.splitlines()[0].endswith(" source=unavailable")
    reasons = [line for line in out.splitlines() if line.startswith("reason=")]
    assert any(line.startswith("reason=projection") for line in reasons)
    assert any(PATH_ENV in line or "ledger" in line for line in reasons)
    assert len(reasons) >= 2


def test_fallback_unreachable_and_unreadable_local_is_unavailable(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setenv(PROJECTION_ENV, _unreachable_url())
    code, out = _call([*CLEAR, "--source", "auto"], monkeypatch, capsys, tmp_path)
    _assert_verdict(code, out, 2, "undecided")
    assert out.splitlines()[0].endswith(" source=unavailable")
    reasons = [line for line in out.splitlines() if line.startswith("reason=")]
    assert any(line.startswith("reason=projection") for line in reasons)
    assert any("unreadable" in line for line in reasons)


def test_fallback_projection_unreachable_never_reads_local_hold(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    local = _write(tmp_path / "local.jsonl", [_line(event) for event in _events()])
    monkeypatch.setenv(PROJECTION_ENV, _unreachable_url())
    code, out = _call([*HELD, "--source", "projection"], monkeypatch, capsys, local)
    _assert_verdict(code, out, 2, "undecided")
    assert out.splitlines()[0].endswith(" source=projection")
    assert any(line.startswith("reason=projection") for line in out.splitlines())
    assert f"hold event={HOLD_ID}" not in out


def test_fallback_unset_projection_url_is_a_fault(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    local = _write(tmp_path / "local.jsonl", [_line(event) for event in _events()])
    monkeypatch.delenv(PROJECTION_ENV, raising=False)
    code, out = _call([*HELD, "--source", "projection"], monkeypatch, capsys, local)
    _assert_verdict(code, out, 2, "undecided")
    assert out.splitlines()[0].endswith(" source=projection")
    assert any(
        PROJECTION_ENV in line
        for line in out.splitlines()
        if line.startswith("reason=")
    )


def test_local_tail_new_hold_changes_clear_to_held(
    projection: ProjectionServer,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    projection.rows = _rows([_epoch(), _claim()])
    local = _write(tmp_path / "local.jsonl", [_line(_epoch()), _line(_hold())])
    monkeypatch.setenv(PROJECTION_ENV, projection.url)
    projection_code, projection_out = _call(
        [*HELD, "--source", "projection"], monkeypatch, capsys, local
    )
    union_code, union_out = _call(
        [*HELD, "--source", "auto"], monkeypatch, capsys, local
    )
    _assert_verdict(projection_code, projection_out, 0, "clear")
    _assert_verdict(union_code, union_out, 3, "held")
    assert " source=union tail=1 watermark=42/45 lag=3" in union_out.splitlines()[0]
    assert f"hold event={HOLD_ID}" in union_out


def test_local_tail_subset_counts_zero(
    projection: ProjectionServer,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    projection.rows = _rows(_events())
    local = _write(tmp_path / "local.jsonl", [_line(_epoch())])
    monkeypatch.setenv(PROJECTION_ENV, projection.url)
    code, out = _call([*HELD, "--source", "auto"], monkeypatch, capsys, local)
    _assert_verdict(code, out, 3, "held")
    assert " source=union tail=0 watermark=42/45 lag=3" in out.splitlines()[0]
    assert out.count(f"hold event={HOLD_ID}") == 1


def test_local_tail_confirmed_hold_is_not_double_counted(
    projection: ProjectionServer,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    projection.rows = _rows(_events())
    local = _write(tmp_path / "local.jsonl", [_line(_epoch()), _line(_hold())])
    monkeypatch.setenv(PROJECTION_ENV, projection.url)
    code, out = _call([*HELD, "--source", "auto"], monkeypatch, capsys, local)
    _assert_verdict(code, out, 3, "held")
    assert " source=union tail=0 watermark=42/45 lag=3" in out.splitlines()[0]
    assert out.count(f"hold event={HOLD_ID}") == 1


def test_local_tail_unparseable_line_is_undecided(
    projection: ProjectionServer,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    projection.rows = _rows([_epoch(), _claim()])
    local = _write(tmp_path / "local.jsonl", [_line(_epoch()), "{not json"])
    monkeypatch.setenv(PROJECTION_ENV, projection.url)
    code, out = _call([*CLEAR, "--source", "auto"], monkeypatch, capsys, local)
    _assert_verdict(code, out, 2, "undecided")
    assert " source=union tail=1 watermark=42/45 lag=3" in out.splitlines()[0]
    assert any(
        "does not parse" in line
        for line in out.splitlines()
        if line.startswith("reason=")
    )


def test_local_tail_absent_buffer_uses_projection(
    projection: ProjectionServer,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    projection.rows = _rows(_events())
    monkeypatch.setenv(PROJECTION_ENV, projection.url)
    code, out = _call([*HELD, "--source", "auto"], monkeypatch, capsys)
    _assert_verdict(code, out, 3, "held")
    assert " source=projection watermark=42/45 lag=3" in out.splitlines()[0]


@pytest.mark.parametrize(
    ("query", "expected", "verdict"),
    [
        (HELD, 3, "held"),
        (["pauses", "--repo", "omnimarket"], 3, "held"),
        (["claims", "--ticket", "OMN-1"], 3, "found"),
        (["inbox", "--lane", "lane-c"], 3, "found"),
        (["surface", "--surface", "dogfood-101"], 0, "clear"),
        (["questions"], 0, "clear"),
        (["health"], 0, "clear"),
    ],
)
def test_local_tail_source_option_is_accepted_by_every_query(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    query: list[str],
    expected: int,
    verdict: str,
) -> None:
    local = _write(tmp_path / "local.jsonl", [_line(event) for event in _events()])
    code, out = _call([*query, "--source", "local"], monkeypatch, capsys, local)
    _assert_verdict(code, out, expected, verdict)
    assert out.splitlines()[0].endswith(" source=local"), out


def test_default_source_leaves_header_unchanged(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    local = _write(tmp_path / "local.jsonl", [_line(event) for event in _events()])
    code, out = _call(HELD, monkeypatch, capsys, local)
    _assert_verdict(code, out, 3, "held")
    assert HEADER.fullmatch(out.splitlines()[0]) is not None
    monkeypatch.setenv(PATH_ENV, str(local))
    with pytest.raises(SystemExit) as exc:
        main(["render", "--check", "--source", "local"])
    assert exc.value.code == 2
    captured = capsys.readouterr()
    assert captured.out == ""
    assert "--source" in captured.err


@pytest.mark.parametrize("url", ["http://[", "ftp://127.0.0.1:1", "not a url"])
def test_probe_malformed_projection_url_is_a_fault_not_a_crash(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    url: str,
) -> None:
    monkeypatch.setenv(PROJECTION_ENV, url)
    code, out = _call([*CLEAR, "--source", "projection"], monkeypatch, capsys)
    _assert_verdict(code, out, 2, "undecided")
    assert out.splitlines()[0].endswith(" source=projection")
    assert any(
        line.startswith("reason=projection URL not configured")
        for line in out.splitlines()
    )
