# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""HandlerDirectModelCallCompute: a structural gate on direct model calls.

OMN-20295. A model call
must sit inside the sanctioned delegation node packages named in
``policy.yaml``. Everywhere else it is refused, whatever words it uses.

The gates-and-delegation readiness audit of 2026-10-01 found
that the earlier gates matched banned literals: a crush shell-out, or a direct
call with no IP, model name or endpoint literal, passed all of them. This
handler reads the AST and the repository's import and call graph instead:

* **Sinks.** A process exec (``subprocess``, ``os.exec*``/``spawn*``/``system``,
  ``asyncio.create_subprocess_*``, ``pexpect``, and every command line of a
  shell file), an HTTP send (an ``httpx``/``requests``/``aiohttp``/``urllib``/
  ``http.client`` call, a ``.post``/``.request``/``.stream`` method, or a
  ``curl``/``wget`` exec), and the import of a model provider SDK.
* **Values.** Each argument is resolved through local and module assignments,
  f-strings, concatenation, ``join``, ``os.path.join``/``urljoin``,
  ``os.environ``/``getenv`` reads, ``shlex.split``, ``shutil.which`` and the
  return values of the repository's own functions, with their parameters
  substituted at each call site.
* **Signals.** An exec is a model call when its program resolves to a model CLI
  (``claude`` only with a print flag), after unwrapping ``env``/``timeout``/
  ``uv run`` and ``sh -c``. An HTTP send is a model call when its URL resolves
  to a model API path or a provider host, or derives from a base-URL source,
  or when its body is a model request (``messages``, or ``model`` with a
  prompt-shaped key).
* **Parameter sinks.** A function whose parameter reaches a sink unresolved
  passes the check to its callers, across files, so a wrapper such as
  ``request_json(url, body)`` is judged at each call with the caller's values.
* **Call graph.** A function that calls a model-calling function in another
  file is a ``call_via`` site, transitively; a file that executes a
  model-calling file of the repository (``python x.py``, ``uv run x.py``) is an
  ``exec_via`` site. A new caller of a baselined site is therefore a new site.

Everything here is PURE and DETERMINISTIC: no filesystem, network, environment
or clock I/O. No inline suppression marker is honoured; ``policy.yaml`` is the
only place a sanctioned package is named.

A call whose URL and body are both opaque at every level (read from a file,
built from runtime data) cannot be seen by any static gate. The backstop for
those is OMN-20299: server-side reconciliation of every model-server request
against a ``delegation_events`` run.
"""

from __future__ import annotations

from omnibase_core.models.nodes.direct_model_call_check.model_direct_model_call_baseline_entry import (
    ModelDirectModelCallBaselineEntry,
)
from omnibase_core.models.nodes.direct_model_call_check.model_direct_model_call_check_input import (
    ModelDirectModelCallCheckInput,
)
from omnibase_core.models.nodes.direct_model_call_check.model_direct_model_call_check_output import (
    ModelDirectModelCallCheckOutput,
)
from omnibase_core.models.nodes.direct_model_call_check.model_direct_model_call_scan_input import (
    ModelDirectModelCallScanInput,
)
from omnibase_core.nodes.node_direct_model_call_check_compute._baseline import (
    added_entries,
    compare_with_baseline,
    entry_problems,
)
from omnibase_core.nodes.node_direct_model_call_check_compute._scan import scan

__all__ = ["HandlerDirectModelCallCompute"]


class HandlerDirectModelCallCompute:
    """COMPUTE handler: a repository's files and baseline in, the verdict out."""

    @property
    def handler_id(self) -> str:
        return "handler_direct_model_call_compute"

    def handle(
        self, request: ModelDirectModelCallCheckInput
    ) -> ModelDirectModelCallCheckOutput:
        """Definition-B entry point: typed request in, typed verdict out, no I/O.

        Raises SyntaxError for a Python file that does not parse: the gate fails
        closed rather than skip it.
        """
        findings = scan(
            request.policy,
            ModelDirectModelCallScanInput(repo=request.repo, files=request.files),
        )
        comparison = compare_with_baseline(findings, request.baseline, request.today)
        problems = entry_problems(request.policy, request.baseline)
        notes: list[str] = []
        grown: list[ModelDirectModelCallBaselineEntry] = []
        if request.base_ref is not None:
            if request.base_baseline is not None:
                grown = added_entries(request.base_baseline, request.baseline)
            elif request.base_wires_gate and request.baseline:
                problems.append(
                    f"{request.baseline_path}: absent at {request.base_ref} although "
                    f"{request.base_ref} already wires this gate; a deleted baseline "
                    "cannot be re-created"
                )
            else:
                notes.append(
                    f"NOTE: {request.baseline_path} does not exist at {request.base_ref} "
                    f"and {request.base_ref} does not wire this gate; this change "
                    "introduces both."
                )
                problems.extend(
                    f"{e.path}: bootstrap entry already expired on {e.expires}"
                    for e in request.baseline
                    if e.expires < request.today
                )
        return ModelDirectModelCallCheckOutput(
            findings=findings,
            new=comparison.new,
            stale=comparison.stale,
            expired=comparison.expired,
            grown=tuple(grown),
            problems=tuple(problems),
            notes=tuple(notes),
            passed=not (
                comparison.new
                or comparison.stale
                or comparison.expired
                or grown
                or problems
            ),
        )
