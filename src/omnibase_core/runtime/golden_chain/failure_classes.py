# SPDX-FileCopyrightText: 2026 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""Formal golden-chain replay failure classes (OMN-13499).

These are the NAMED, RAISEABLE failure classes the canonical replay harness uses
so a migration failure is debuggable and a broken route cannot be masked by a
"replay succeeds anyway" outcome.

The classes are deliberately small and explicit (no string-typed error soup):

* ``INVALID_FIXTURE``      — the fixture file is missing, unparseable, or its
  provenance bundle is incomplete / internally inconsistent.
* ``EMPTY_COMPLETION``     — the recorded completion bytes are empty/whitespace.
  A golden chain proving an empty model response is proving nothing.
* ``ECHO_COMPLETION``      — the recorded completion merely echoes the prompt
  (the classic hand-written-fake tell). Recorded-from-real bytes are never an
  echo of the request.
* ``ROUTE_NOT_RESOLVED``   — the live path posted to an endpoint the fixture was
  not recorded for, OR a delegation TIER name reached the inference layer as a
  ``model_key`` (the OMN-13470 bug class). The route the live path resolved does
  not match a recorded concrete route.
* ``REQUEST_HASH_MISMATCH`` — the live-constructed request hash differs from the
  recorded ``request_hash``. The routing/selection/request-construction drifted
  (e.g. a wrong model, wrong max_tokens, wrong messages) so the recorded bytes
  are NOT evidence for this request. This is the load-bearing proof that replay
  is evidence, not authority.
"""

from __future__ import annotations

from enum import Enum


class EnumGoldenChainFailureClass(str, Enum):
    """Named failure classes raised by the canonical golden-chain replay harness."""

    INVALID_FIXTURE = "INVALID_FIXTURE"
    EMPTY_COMPLETION = "EMPTY_COMPLETION"
    ECHO_COMPLETION = "ECHO_COMPLETION"
    ROUTE_NOT_RESOLVED = "ROUTE_NOT_RESOLVED"
    REQUEST_HASH_MISMATCH = "REQUEST_HASH_MISMATCH"


class GoldenChainReplayError(RuntimeError):
    """A golden-chain replay failed in a named, classified way.

    Carries the ``EnumGoldenChainFailureClass`` so callers (and the planted
    routing-failure proof test) can assert the EXACT failure class rather than
    matching on substrings. The string form is ``"<FAILURE_CLASS>: <message>"``.
    """

    def __init__(
        self, failure_class: EnumGoldenChainFailureClass, message: str
    ) -> None:
        self.failure_class = failure_class
        super().__init__(f"{failure_class.value}: {message}")


__all__ = ["EnumGoldenChainFailureClass", "GoldenChainReplayError"]
