<!-- SPDX-FileCopyrightText: 2025 OmniNode.ai Inc. -->
<!-- SPDX-License-Identifier: MIT -->
<!-- doc-content-file-ok: design doc; Linear ticket references (OMN-14355/14353/14208) are intentional provenance -->

# Adequacy receipts (OMN-14355)

One committed `<node_id>.json` per node that has flipped **non-canonical → canonical**
in the canonical handler-shape ratchet baseline
(`scripts/ci/canonical_handler_shape_baseline.py`).

A node may only leave the frozen `NON_CANONICAL` set with a receipt here — a shape
flip alone is **not** proof of equivalence (the OMN-14208-at-scale trap). Each file
is a serialized `ModelAdequacyReceipt` (`scripts/ci/adequacy_receipt.py`, OMN-14353)
and must satisfy, at check time (`canonical_handler_shape.py`):

- `node_id` equals the flipped node;
- `meets_target` is true (branch coverage ≥ target) **or** `uncovered_waiver` is
  present (a visible, operator-reviewed waiver — never a silent below-target pass);
- `handler_module_sha256` re-computes to the same value on the live handler source
  (a stale receipt recorded against old code is rejected).

Produce a receipt with the recorder in `scripts/ci/adequacy_receipt.py`
(`build_receipt(...)`), then run `canonical_handler_shape.py --update` to drop the
node from the baseline.
